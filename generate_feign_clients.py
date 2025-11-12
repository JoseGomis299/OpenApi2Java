#!/usr/bin/env python3
"""
Generate Feign Client interfaces from OpenAPI specification.
Creates Spring Cloud OpenFeign clients for all endpoints defined in the OpenAPI spec.
"""
import os
import yaml
import re
from config import get_config

def to_java_class_name(name):
    """Convert string to Java class name."""
    if re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
        return name
    if re.match(r'^[a-z][a-zA-Z0-9]*$', name):
        return name[0].upper() + name[1:]
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    parts = re.split(r'[_\s-]+', name)
    return ''.join(word.capitalize() for word in parts if word)

def to_java_method_name(operation_id):
    """Convert operationId to Java method name."""
    if not operation_id:
        return "execute"
    # If already in camelCase, keep it
    if re.match(r'^[a-z][a-zA-Z0-9]*$', operation_id):
        return operation_id
    # Convert to camelCase
    name = re.sub(r'[^a-zA-Z0-9_]', '_', operation_id)
    parts = re.split(r'[_\s-]+', name)
    if not parts:
        return operation_id
    return parts[0].lower() + ''.join(word.capitalize() for word in parts[1:] if word)

def to_java_param_name(name):
    """Convert parameter name to valid Java identifier (camelCase), preserving internal camelCase."""
    if not name:
        return "param"
    # If already valid camelCase, keep it
    if re.match(r'^[a-z][a-zA-Z0-9]*$', name):
        return name

    # Split by hyphens, underscores, and spaces while preserving camelCase within parts
    # First replace hyphens and spaces with underscores for uniform splitting
    name = name.replace('-', '_').replace(' ', '_')
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    parts = [part for part in name.split('_') if part]

    if not parts:
        return "param"

    # First part should be lowercase, rest should preserve their camelCase or capitalize if all lowercase
    result_parts = []
    for i, part in enumerate(parts):
        if i == 0:
            # First part: convert to lowercase
            result_parts.append(part.lower())
        else:
            # Subsequent parts: preserve if already has uppercase (camelCase), otherwise capitalize first letter
            if any(c.isupper() for c in part):
                # Has uppercase letters - preserve as is (e.g., "applicationId" stays "applicationId")
                # But ensure first letter is uppercase for concatenation
                result_parts.append(part[0].upper() + part[1:] if part else '')
            else:
                # All lowercase - capitalize first letter
                result_parts.append(part.capitalize())

    return ''.join(result_parts)

def get_java_type_from_schema(schema, schemas, components):
    """Determine Java type from schema reference or inline schema."""
    if '$ref' in schema:
        ref_path = schema['$ref'].split('/')
        if ref_path[-2] == 'schemas':
            class_name = to_java_class_name(ref_path[-1])
            # Check if this schema has oneOf fields and needs generic definition
            schema_name = ref_path[-1]
            if schema_name in schemas:
                actual_schema = schemas[schema_name]
                # Only check for oneOf, don't recurse
                if has_oneof_property(actual_schema):
                    base_class = get_oneof_base_class_name(actual_schema)
                    if base_class:
                        return f"{class_name}<? extends {base_class}>"
            return class_name
        elif ref_path[-2] == 'parameters':
            return 'String'  # Default for parameters

    schema_type = schema.get('type', 'object')

    if schema_type == 'array':
        if 'items' in schema:
            item_type = get_java_type_from_schema(schema['items'], schemas, components)
            return f"List<{item_type}>"
        return "List<Object>"

    type_mapping = {
        'string': 'String',
        'integer': 'Integer',
        'number': 'Double',
        'boolean': 'Boolean',
        'object': 'Object'
    }

    return type_mapping.get(schema_type, 'Object')

def has_oneof_property(schema):
    """Check if schema has any property with oneOf, including in allOf."""
    # Check direct properties
    properties = schema.get('properties', {})
    for prop_schema in properties.values():
        if 'oneOf' in prop_schema:
            return True

    # Check allOf items
    if 'allOf' in schema:
        for item in schema['allOf']:
            # If it's an inline object with properties
            if isinstance(item, dict) and 'properties' in item:
                for prop_schema in item['properties'].values():
                    if 'oneOf' in prop_schema:
                        return True

    return False

def get_oneof_base_class_name(schema):
    """Get the base class name from the first oneOf property found, including in allOf."""
    # Check direct properties
    properties = schema.get('properties', {})
    for prop_name, prop_schema in properties.items():
        if 'oneOf' in prop_schema:
            return to_java_class_name(prop_name)

    # Check allOf items
    if 'allOf' in schema:
        for item in schema['allOf']:
            # If it's an inline object with properties
            if isinstance(item, dict) and 'properties' in item:
                for prop_name, prop_schema in item['properties'].items():
                    if 'oneOf' in prop_schema:
                        return to_java_class_name(prop_name)

    return None

def resolve_ref(ref, openapi_spec):
    """Resolve a $ref to its actual value in the OpenAPI spec."""
    parts = ref.split('/')
    result = openapi_spec
    for part in parts:
        if part == '#':
            continue
        result = result.get(part, {})
    return result

def get_parameter_info(param_or_ref, openapi_spec):
    """Get parameter information, resolving references if needed."""
    if '$ref' in param_or_ref:
        return resolve_ref(param_or_ref['$ref'], openapi_spec)
    return param_or_ref

def get_response_type(responses, schemas, components):
    """Get the response type from responses object."""
    # Look for successful response (200, 201, etc.)
    for status_code in ['200', '201', '202', '203', '204']:
        if status_code in responses:
            response = responses[status_code]

            # Handle reference to response
            if '$ref' in response:
                ref_name = response['$ref'].split('/')[-1]
                response = components.get('responses', {}).get(ref_name, {})

            # Get content
            content = response.get('content', {})
            json_content = content.get('application/json', {})

            if 'schema' in json_content:
                schema = json_content['schema']
                return get_java_type_from_schema(schema, schemas, components)

    return 'void'

def generate_javadoc(summary, description, parameters=None, return_type=None, openapi_spec=None):
    """Generate JavaDoc comment."""
    lines = ["/**"]

    if summary:
        lines.append(f" * {summary}")

    if description and description != summary:
        lines.append(" *")
        # Split long descriptions
        for line in description.split('\n'):
            if line.strip():
                lines.append(f" * {line.strip()}")

    if parameters:
        lines.append(" *")
        for param_info in parameters:
            if isinstance(param_info, dict):
                param = param_info
            else:
                param = get_parameter_info(param_info, openapi_spec) if openapi_spec else param_info

            param_name = param.get('name', 'unknown')
            param_java_name = to_java_param_name(param_name)  # Convert to valid Java identifier
            param_desc = param.get('description', '')
            if param_desc:
                lines.append(f" * @param {param_java_name} {param_desc}")
            else:
                lines.append(f" * @param {param_java_name}")

    if return_type and return_type != 'void':
        lines.append(f" * @return {return_type}")

    lines.append(" */")
    return '\n'.join(lines)

def get_request_body_type(request_body, schemas, components):
    """Get the Java type for request body."""
    if not request_body:
        return None

    # Handle reference to request body
    if '$ref' in request_body:
        ref_name = request_body['$ref'].split('/')[-1]
        request_body = components.get('requestBodies', {}).get(ref_name, {})

    content = request_body.get('content', {})
    json_content = content.get('application/json', {})

    if 'schema' in json_content:
        schema = json_content['schema']
        return get_java_type_from_schema(schema, schemas, components)

    return None

def generate_feign_client(tag, paths_by_tag, openapi_spec, config):
    """Generate a Feign client interface for a specific tag."""
    base_package = config['feign']['base_package']
    enable_javadoc = config['feign']['enable_javadoc']
    interface_suffix = config['feign']['interface_suffix']
    use_response_entity = config['feign'].get('use_response_entity', False)
    format_one_param_per_line = config['feign'].get('format_one_param_per_line', True)
    add_feign_annotation = config['feign'].get('add_feign_annotation', True)
    ignore_optional_params = config['feign'].get('ignore_optional_params', False)
    ignore_params_list = config['feign'].get('ignore_params_list', [])

    schemas = openapi_spec.get('components', {}).get('schemas', {})
    components = openapi_spec.get('components', {})

    # Generate class name from tag
    client_name = to_java_class_name(tag) + interface_suffix

    # Start building the interface
    lines = []
    lines.append(f"package {base_package};")
    lines.append("")

    # Imports
    imports = set([
        "org.springframework.web.bind.annotation.*"
    ])

    # Only add FeignClient import if annotation is enabled
    if add_feign_annotation:
        imports.add("org.springframework.cloud.openfeign.FeignClient")

    # Only import ResponseEntity if needed
    if use_response_entity:
        imports.add("org.springframework.http.ResponseEntity")

    # Check if we need List import
    has_lists = False
    for path, methods in paths_by_tag:
        for method, operation in methods.items():
            # Check parameters
            for param_or_ref in operation.get('parameters', []):
                param = get_parameter_info(param_or_ref, openapi_spec)
                schema = param.get('schema', {})
                if schema.get('type') == 'array':
                    has_lists = True

            # Check request body
            request_body_type = get_request_body_type(operation.get('requestBody'), schemas, components)
            if request_body_type and 'List<' in str(request_body_type):
                has_lists = True

            # Check response
            response_type = get_response_type(operation.get('responses', {}), schemas, components)
            if 'List<' in str(response_type):
                has_lists = True

    if has_lists:
        imports.add("java.util.List")

    for imp in sorted(imports):
        lines.append(f"import {imp};")

    lines.append("")

    # Interface JavaDoc
    if enable_javadoc:
        info = openapi_spec.get('info', {})
        title = info.get('title', 'API')
        description = info.get('description', '')

        lines.append("/**")
        lines.append(f" * Feign client for {tag} operations.")
        if description:
            lines.append(f" * {description}")
        lines.append(" */")

    # FeignClient annotation (conditional)
    if add_feign_annotation:
        # Use tag name as the client name (converted to lowercase)
        feign_client_name = tag.lower().replace(' ', '-')
        lines.append(f'@FeignClient(name = "{feign_client_name}", url = "${{feign.client.{feign_client_name}.url}}")')

    lines.append(f"public interface {client_name} {{")
    lines.append("")

    # Generate methods for each operation
    for path, methods in paths_by_tag:
        for http_method, operation in methods.items():
            operation_id = operation.get('operationId', f"{http_method}_{path.replace('/', '_')}")
            method_name = to_java_method_name(operation_id)

            summary = operation.get('summary', '')
            description = operation.get('description', '')

            # Get parameters
            params = []
            method_params = []

            for param_or_ref in operation.get('parameters', []):
                param = get_parameter_info(param_or_ref, openapi_spec)
                param_name = param.get('name', 'unknown')
                param_java_name = to_java_param_name(param_name)  # Convert to valid Java identifier
                param_in = param.get('in', 'query')
                required = param.get('required', False)
                param_schema = param.get('schema', {})
                param_type = get_java_type_from_schema(param_schema, schemas, components)

                # Skip parameter if it should be ignored
                if param_name in ignore_params_list:
                    continue

                # Skip optional parameters if configured to ignore them
                if ignore_optional_params and not required:
                    continue

                params.append(param)

                # Create parameter annotation
                if param_in == 'path':
                    annotation = f'@PathVariable("{param_name}")'
                elif param_in == 'query':
                    if required:
                        annotation = f'@RequestParam("{param_name}")'
                    else:
                        annotation = f'@RequestParam(value = "{param_name}", required = false)'
                elif param_in == 'header':
                    if required:
                        annotation = f'@RequestHeader("{param_name}")'
                    else:
                        annotation = f'@RequestHeader(value = "{param_name}", required = false)'
                else:
                    annotation = f'@RequestParam("{param_name}")'

                method_params.append(f"{annotation} {param_type} {param_java_name}")

            # Check for request body
            request_body = operation.get('requestBody')
            request_body_type = get_request_body_type(request_body, schemas, components)

            if request_body_type:
                method_params.append(f"@RequestBody {request_body_type} body")

            # Get response type
            response_type = get_response_type(operation.get('responses', {}), schemas, components)
            if use_response_entity:
                return_type = f"ResponseEntity<{response_type}>" if response_type != 'void' else "ResponseEntity<Void>"
            else:
                return_type = response_type

            # Generate JavaDoc
            if enable_javadoc:
                javadoc = generate_javadoc(summary, description, params, response_type, openapi_spec)
                for line in javadoc.split('\n'):
                    lines.append(f"    {line}")

            # Generate mapping annotation
            mapping_method = http_method.lower().capitalize()
            if mapping_method == 'Get':
                mapping = 'GetMapping'
            elif mapping_method == 'Post':
                mapping = 'PostMapping'
            elif mapping_method == 'Put':
                mapping = 'PutMapping'
            elif mapping_method == 'Delete':
                mapping = 'DeleteMapping'
            elif mapping_method == 'Patch':
                mapping = 'PatchMapping'
            else:
                mapping = 'RequestMapping'

            lines.append(f'    @{mapping}("{path}")')

            # Generate method signature
            if format_one_param_per_line and len(method_params) > 0:
                # Format with one parameter per line
                lines.append(f"    {return_type} {method_name}(")
                for i, param in enumerate(method_params):
                    if i < len(method_params) - 1:
                        lines.append(f"        {param},")
                    else:
                        lines.append(f"        {param}")
                lines.append("    );")
            else:
                # Single line format
                params_str = ', '.join(method_params)
                lines.append(f"    {return_type} {method_name}({params_str});")
            lines.append("")

    lines.append("}")

    return '\n'.join(lines)

def generate_single_api_client(all_paths, openapi_spec, config):
    """Generate a single Feign client interface for the entire API."""
    base_package = config['feign']['base_package']
    enable_javadoc = config['feign']['enable_javadoc']
    interface_suffix = config['feign']['interface_suffix']
    use_response_entity = config['feign'].get('use_response_entity', False)
    format_one_param_per_line = config['feign'].get('format_one_param_per_line', True)
    add_feign_annotation = config['feign'].get('add_feign_annotation', True)
    ignore_optional_params = config['feign'].get('ignore_optional_params', False)
    ignore_params_list = config['feign'].get('ignore_params_list', [])

    schemas = openapi_spec.get('components', {}).get('schemas', {})
    components = openapi_spec.get('components', {})

    # Generate class name from API title
    api_title = openapi_spec.get('info', {}).get('title', 'Api')
    client_name = to_java_class_name(api_title.replace(' ', '')) + interface_suffix

    # Group operations by tag for organization
    operations_by_tag = {}
    for path, path_item in all_paths:
        for method in ['get', 'post', 'put', 'delete', 'patch']:
            if method not in path_item:
                continue

            operation = path_item[method]
            tags = operation.get('tags', ['Default'])

            for tag in tags:
                if tag not in operations_by_tag:
                    operations_by_tag[tag] = []
                operations_by_tag[tag].append((path, method, operation))

    # Start building the interface
    lines = []
    lines.append(f"package {base_package};")
    lines.append("")

    # Imports
    imports = set([
        "org.springframework.web.bind.annotation.*"
    ])

    # Only add FeignClient import if annotation is enabled
    if add_feign_annotation:
        imports.add("org.springframework.cloud.openfeign.FeignClient")

    # Only import ResponseEntity if needed
    if use_response_entity:
        imports.add("org.springframework.http.ResponseEntity")

    # Check if we need List import
    has_lists = False
    for path, path_item in all_paths:
        for method in ['get', 'post', 'put', 'delete', 'patch']:
            if method not in path_item:
                continue
            operation = path_item[method]

            # Check parameters
            for param_or_ref in operation.get('parameters', []):
                param = get_parameter_info(param_or_ref, openapi_spec)
                schema = param.get('schema', {})
                if schema.get('type') == 'array':
                    has_lists = True

            # Check request body
            request_body_type = get_request_body_type(operation.get('requestBody'), schemas, components)
            if request_body_type and 'List<' in str(request_body_type):
                has_lists = True

            # Check response
            response_type = get_response_type(operation.get('responses', {}), schemas, components)
            if 'List<' in str(response_type):
                has_lists = True

    if has_lists:
        imports.add("java.util.List")

    for imp in sorted(imports):
        lines.append(f"import {imp};")

    lines.append("")

    # Interface JavaDoc
    if enable_javadoc:
        info = openapi_spec.get('info', {})
        title = info.get('title', 'API')
        description = info.get('description', '')

        lines.append("/**")
        lines.append(f" * Feign client for {title}.")
        if description:
            lines.append(f" * {description}")
        lines.append(" */")

    # FeignClient annotation (conditional)
    if add_feign_annotation:
        api_name = api_title.lower().replace(' ', '-')
        lines.append(f'@FeignClient(name = "{api_name}", url = "${{feign.client.{api_name}.url}}")')

    lines.append(f"public interface {client_name} {{")
    lines.append("")

    # Generate methods grouped by tag
    for tag in sorted(operations_by_tag.keys()):
        operations = operations_by_tag[tag]

        # Add tag section comment
        lines.append(f"    // ========================================")
        lines.append(f"    // {tag}")
        lines.append(f"    // ========================================")
        lines.append("")

        for path, http_method, operation in operations:
            operation_id = operation.get('operationId', f"{http_method}_{path.replace('/', '_')}")
            method_name = to_java_method_name(operation_id)

            summary = operation.get('summary', '')
            description = operation.get('description', '')

            # Get parameters
            params = []
            method_params = []

            for param_or_ref in operation.get('parameters', []):
                param = get_parameter_info(param_or_ref, openapi_spec)
                param_name = param.get('name', 'unknown')
                param_java_name = to_java_param_name(param_name)
                param_in = param.get('in', 'query')
                required = param.get('required', False)
                param_schema = param.get('schema', {})
                param_type = get_java_type_from_schema(param_schema, schemas, components)

                # Skip parameter if it should be ignored
                if param_name in ignore_params_list:
                    continue

                # Skip optional parameters if configured to ignore them
                if ignore_optional_params and not required:
                    continue

                params.append(param)

                # Create parameter annotation
                if param_in == 'path':
                    annotation = f'@PathVariable("{param_name}")'
                elif param_in == 'query':
                    if required:
                        annotation = f'@RequestParam("{param_name}")'
                    else:
                        annotation = f'@RequestParam(value = "{param_name}", required = false)'
                elif param_in == 'header':
                    if required:
                        annotation = f'@RequestHeader("{param_name}")'
                    else:
                        annotation = f'@RequestHeader(value = "{param_name}", required = false)'
                else:
                    annotation = f'@RequestParam("{param_name}")'

                method_params.append(f"{annotation} {param_type} {param_java_name}")

            # Check for request body
            request_body = operation.get('requestBody')
            request_body_type = get_request_body_type(request_body, schemas, components)

            if request_body_type:
                method_params.append(f"@RequestBody {request_body_type} body")

            # Get response type
            response_type = get_response_type(operation.get('responses', {}), schemas, components)
            if use_response_entity:
                return_type = f"ResponseEntity<{response_type}>" if response_type != 'void' else "ResponseEntity<Void>"
            else:
                return_type = response_type

            # Generate JavaDoc
            if enable_javadoc:
                javadoc = generate_javadoc(summary, description, params, response_type, openapi_spec)
                for line in javadoc.split('\n'):
                    lines.append(f"    {line}")

            # Generate mapping annotation
            mapping_method = http_method.lower().capitalize()
            if mapping_method == 'Get':
                mapping = 'GetMapping'
            elif mapping_method == 'Post':
                mapping = 'PostMapping'
            elif mapping_method == 'Put':
                mapping = 'PutMapping'
            elif mapping_method == 'Delete':
                mapping = 'DeleteMapping'
            elif mapping_method == 'Patch':
                mapping = 'PatchMapping'
            else:
                mapping = 'RequestMapping'

            lines.append(f'    @{mapping}("{path}")')

            # Generate method signature
            if format_one_param_per_line and len(method_params) > 0:
                # Format with one parameter per line
                lines.append(f"    {return_type} {method_name}(")
                for i, param in enumerate(method_params):
                    if i < len(method_params) - 1:
                        lines.append(f"        {param},")
                    else:
                        lines.append(f"        {param}")
                lines.append("    );")
            else:
                # Single line format
                params_str = ', '.join(method_params)
                lines.append(f"    {return_type} {method_name}({params_str});")
            lines.append("")

    lines.append("}")

    return '\n'.join(lines)

def generate_feign_configuration(config):
    """Generate FeignConfiguration class with common settings."""
    base_package = config['feign']['base_package']

    lines = []
    lines.append(f"package {base_package}.config;")
    lines.append("")
    lines.append("import feign.Logger;")
    lines.append("import feign.RequestInterceptor;")
    lines.append("import feign.codec.ErrorDecoder;")
    lines.append("import org.springframework.context.annotation.Bean;")
    lines.append("import org.springframework.context.annotation.Configuration;")
    lines.append("")
    lines.append("/**")
    lines.append(" * Common Feign client configuration.")
    lines.append(" */")
    lines.append("@Configuration")
    lines.append("public class FeignConfiguration {")
    lines.append("")
    lines.append("    /**")
    lines.append("     * Set Feign logging level.")
    lines.append("     */")
    lines.append("    @Bean")
    lines.append("    public Logger.Level feignLoggerLevel() {")
    lines.append("        return Logger.Level.FULL;")
    lines.append("    }")
    lines.append("")
    lines.append("    /**")
    lines.append("     * Custom error decoder for Feign clients.")
    lines.append("     */")
    lines.append("    @Bean")
    lines.append("    public ErrorDecoder errorDecoder() {")
    lines.append("        return new ErrorDecoder.Default();")
    lines.append("    }")
    lines.append("")
    lines.append("}")

    return '\n'.join(lines)

def process_single_openapi_for_feign(openapi_file, output_dir, config):
    """Process a single OpenAPI definition for Feign client generation."""

    # Load OpenAPI spec
    if not os.path.exists(openapi_file):
        print(f"❌ {openapi_file} not found!")
        return

    with open(openapi_file, 'r', encoding='utf-8') as f:
        openapi_spec = yaml.safe_load(f)

    base_package = config['feign']['base_package']
    generate_config_class = config['feign']['generate_config']
    grouping_strategy = config['feign'].get('grouping_strategy', 'by-tag')

    # Get all paths
    paths = openapi_spec.get('paths', {})

    if grouping_strategy == 'single-client':
        # Generate a single client for entire API
        print(f"  📝 Generating single Feign client for entire API")

        all_paths = [(path, path_item) for path, path_item in paths.items()]
        client_code = generate_single_api_client(all_paths, openapi_spec, config)

        # Write to file
        api_title = openapi_spec.get('info', {}).get('title', 'Api')
        client_name = to_java_class_name(api_title.replace(' ', '')) + config['feign']['interface_suffix']
        file_path = os.path.join(output_dir, f"{client_name}.java")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(client_code)

        print(f"     ✅ Created {file_path}")
    else:
        # Generate one client per tag (default behavior)
        tags_dict = {}

        for path, path_item in paths.items():
            for method in ['get', 'post', 'put', 'delete', 'patch']:
                if method in path_item:
                    operation = path_item[method]
                    operation_tags = operation.get('tags', ['Default'])

                    for tag in operation_tags:
                        if tag not in tags_dict:
                            tags_dict[tag] = []
                        tags_dict[tag].append((path, {method: operation}))

        # Generate a Feign client for each tag
        for tag, paths_by_tag in tags_dict.items():
            print(f"  📝 Generating Feign client for tag: {tag}")

            client_code = generate_feign_client(tag, paths_by_tag, openapi_spec, config)

            # Write to file
            client_name = to_java_class_name(tag) + config['feign']['interface_suffix']
            file_path = os.path.join(output_dir, f"{client_name}.java")

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(client_code)

            print(f"     ✅ Created {file_path}")

    # Generate configuration class if enabled
    if generate_config_class:
        print(f"  📝 Generating Feign configuration class")
        config_dir = os.path.join(output_dir, 'config')
        os.makedirs(config_dir, exist_ok=True)

        config_code = generate_feign_configuration(config)
        config_file = os.path.join(config_dir, 'FeignConfiguration.java')

        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_code)

        print(f"     ✅ Created {config_file}")

def main():
    """Main function to generate Feign clients."""
    # Load configuration
    from config import get_config, get_openapi_definition_files

    config = get_config()

    base_feign_folder = config['feign']['feign_folder']
    base_package = config['feign']['base_package']
    grouping_strategy = config['feign'].get('grouping_strategy', 'single-client')

    print(f"🚀 Generating Feign clients...")
    print(f"   📋 Grouping strategy: {grouping_strategy}\n")

    definition_files = get_openapi_definition_files()

    if not definition_files:
        print("❌ No OpenAPI definition files found!")
        return

    print(f"🚀 Processing {len(definition_files)} definition(s)...\n")

    for name, file_path in definition_files:
        # Create subdirectory for this definition
        output_dir = os.path.join(base_feign_folder, name)
        print(f"\n{'='*60}")
        print(f"📋 Processing: {name} ({file_path})")
        print(f"{'='*60}\n")

        # Create output directory
        if os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        process_single_openapi_for_feign(file_path, output_dir, config)

    print(f"\n{'='*60}")
    print(f"✅ Feign client generation complete!")
    print(f"   📁 Output directory: {base_feign_folder}")
    print(f"   📦 Base package: {base_package}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()

