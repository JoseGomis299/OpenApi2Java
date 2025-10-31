import json
import yaml
import os
from datetime import datetime
from collections import defaultdict


def extract_endpoints_from_openapi(openapi_definition):
    """Extract endpoints with their request/response schemas."""
    endpoints = []
    paths = openapi_definition.get('paths', {})

    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method not in ['get', 'post', 'put', 'patch', 'delete']:
                continue

            # Generate endpoint name: METHOD_endpointName
            endpoint_parts = [p for p in path.split('/') if p and not p.startswith('{')]
            endpoint_name = f"{method.upper()}_{'_'.join(endpoint_parts)}" if endpoint_parts else f"{method.upper()}_root"

            # Extract request body schema
            request_schema = None
            request_body = operation.get('requestBody', {})
            if request_body:
                content = request_body.get('content', {})
                json_content = content.get('application/json', {})
                schema = json_content.get('schema', {})
                if '$ref' in schema:
                    request_schema = schema['$ref'].split('/')[-1]

            # Extract response schemas (200, 201, etc.)
            response_schemas = []
            responses = operation.get('responses', {})

            # Get components/responses for lookup
            responses_comp = openapi_definition.get('components', {}).get('responses', {})

            for status_code, response in responses.items():
                if status_code.startswith('2'):  # 2xx responses
                    if '$ref' in response:
                        # Response is a reference
                        ref_name = response['$ref'].split('/')[-1]
                        if ref_name in responses_comp:
                            resp_content = responses_comp[ref_name].get('content', {})
                            json_content = resp_content.get('application/json', {})
                            schema = json_content.get('schema', {})
                            if '$ref' in schema:
                                response_schemas.append(schema['$ref'].split('/')[-1])
                    else:
                        # Direct response definition
                        resp_content = response.get('content', {})
                        json_content = resp_content.get('application/json', {})
                        schema = json_content.get('schema', {})
                        if '$ref' in schema:
                            response_schemas.append(schema['$ref'].split('/')[-1])

            endpoint = {
                'name': endpoint_name,
                'path': path,
                'method': method,
                'requestSchema': request_schema,
                'responseSchemas': response_schemas
            }

            endpoints.append(endpoint)

    return endpoints


def get_schema_dependencies(schema_name, schemas, visited=None):
    """Get all dependencies (referenced schemas) of a schema recursively."""
    if visited is None:
        visited = set()

    if schema_name in visited or schema_name not in schemas:
        return visited

    visited.add(schema_name)
    schema = schemas[schema_name]

    # Handle allOf
    if 'allOf' in schema:
        for sub_schema in schema['allOf']:
            if '$ref' in sub_schema:
                ref_name = sub_schema['$ref'].split('/')[-1]
                get_schema_dependencies(ref_name, schemas, visited)
            elif isinstance(sub_schema, dict) and 'properties' in sub_schema:
                extract_refs_from_properties(sub_schema.get('properties', {}), schemas, visited)

    # Handle oneOf - INCLUDE ALL OPTIONS
    if 'oneOf' in schema:
        for sub_schema in schema['oneOf']:
            if '$ref' in sub_schema:
                ref_name = sub_schema['$ref'].split('/')[-1]
                get_schema_dependencies(ref_name, schemas, visited)

    # Handle anyOf - INCLUDE ALL OPTIONS
    if 'anyOf' in schema:
        for sub_schema in schema['anyOf']:
            if '$ref' in sub_schema:
                ref_name = sub_schema['$ref'].split('/')[-1]
                get_schema_dependencies(ref_name, schemas, visited)

    # Handle properties
    if 'properties' in schema:
        extract_refs_from_properties(schema['properties'], schemas, visited)

    return visited


def extract_refs_from_properties(properties, schemas, visited):
    """Extract all $ref from properties, including oneOf/anyOf."""
    for prop_name, prop_schema in properties.items():
        # Direct $ref
        if '$ref' in prop_schema:
            ref_name = prop_schema['$ref'].split('/')[-1]
            get_schema_dependencies(ref_name, schemas, visited)

        # Array with items
        if prop_schema.get('type') == 'array' and 'items' in prop_schema:
            if '$ref' in prop_schema['items']:
                ref_name = prop_schema['items']['$ref'].split('/')[-1]
                get_schema_dependencies(ref_name, schemas, visited)

        # oneOf in property
        if 'oneOf' in prop_schema:
            for one_of_schema in prop_schema['oneOf']:
                if '$ref' in one_of_schema:
                    ref_name = one_of_schema['$ref'].split('/')[-1]
                    get_schema_dependencies(ref_name, schemas, visited)

        # anyOf in property
        if 'anyOf' in prop_schema:
            for any_of_schema in prop_schema['anyOf']:
                if '$ref' in any_of_schema:
                    ref_name = any_of_schema['$ref'].split('/')[-1]
                    get_schema_dependencies(ref_name, schemas, visited)

        # allOf in property
        if 'allOf' in prop_schema:
            for all_of_schema in prop_schema['allOf']:
                if '$ref' in all_of_schema:
                    ref_name = all_of_schema['$ref'].split('/')[-1]
                    get_schema_dependencies(ref_name, schemas, visited)


def load_openapi_definition(file_path):
    """Load the OpenAPI definition from a file (JSON or YAML)."""
    with open(file_path, 'r') as file:
        if file_path.endswith('.json'):
            return json.load(file)
        elif file_path.endswith(('.yaml', '.yml')):
            return yaml.safe_load(file)
        else:
            raise ValueError("File must be in JSON or YAML format")


def extract_schemas(openapi_definition):
    """Extract schemas from the OpenAPI definition."""
    return openapi_definition.get('components', {}).get('schemas', {})


def generate_example_from_schema(schema, schemas, seen_refs=None):
    """
    Recursively generate example JSON for a schema.
    Fully resolves $refs and builds a dependency tree of examples.
    """
    if seen_refs is None:
        seen_refs = set()

    if not schema:
        return None

    # Handle $ref
    if '$ref' in schema:
        ref_path = schema['$ref'].split('/')

        # Handle property-level references like #/components/schemas/Schema/properties/propertyName
        if len(ref_path) > 3 and ref_path[-2] == 'properties':
            schema_name = ref_path[-3]
            property_name = ref_path[-1]
            ref_schema = schemas.get(schema_name, {})
            property_schema = ref_schema.get('properties', {}).get(property_name, {})
            if property_schema:
                return generate_example_from_schema(property_schema, schemas, seen_refs)

        # Handle normal schema-level references
        ref_name = ref_path[-1]
        if ref_name in seen_refs:
            # Avoid infinite recursion in circular references
            return f"# circular reference to {ref_name}"
        seen_refs.add(ref_name)
        ref_schema = schemas.get(ref_name, {})
        return generate_example_from_schema(ref_schema, schemas, seen_refs)

    # Handle allOf - merge all schemas
    if 'allOf' in schema:
        # Special case: if allOf has only one element, just return that
        if len(schema['allOf']) == 1:
            return generate_example_from_schema(schema['allOf'][0], schemas, seen_refs.copy())

        # Otherwise, merge multiple schemas (assuming they're all objects)
        merged_example = {}
        for sub_schema in schema['allOf']:
            sub_example = generate_example_from_schema(sub_schema, schemas, seen_refs.copy())
            if isinstance(sub_example, dict):
                merged_example.update(sub_example)
            elif sub_example is not None:
                # If we encounter a non-dict type in allOf with multiple schemas,
                # we can't merge it, so just return it
                return sub_example
        return merged_example

    # Handle oneOf - use the first schema
    if 'oneOf' in schema:
        if schema['oneOf']:
            return generate_example_from_schema(schema['oneOf'][0], schemas, seen_refs.copy())

    # Handle anyOf - use the first schema
    if 'anyOf' in schema:
        if schema['anyOf']:
            return generate_example_from_schema(schema['anyOf'][0], schemas, seen_refs.copy())

    # Example field (highest priority)
    if 'example' in schema:
        return schema['example']

    # Enum
    if 'enum' in schema:
        return schema['enum'][0]

    # Default
    if 'default' in schema:
        return schema['default']

    schema_type = schema.get('type', 'object')

    # Handle object schemas
    if schema_type == 'object':
        example_obj = {}
        props = schema.get('properties', {})
        for prop_name, prop_schema in props.items():
            example_obj[prop_name] = generate_example_from_schema(prop_schema, schemas, seen_refs.copy())
        return example_obj

    # Handle arrays
    if schema_type == 'array':
        item_schema = schema.get('items', {})
        return [generate_example_from_schema(item_schema, schemas, seen_refs.copy())]

    # Primitive types
    if schema_type == 'string':
        fmt = schema.get('format', '')
        if fmt == 'date-time':
            return "2025-01-01T00:00:00Z"
        elif fmt == 'date':
            return "2025-01-01"
        elif fmt == 'email':
            return "user@example.com"
        elif fmt == 'uuid':
            return "123e4567-e89b-12d3-a456-426614174000"
        else:
            return "example_string"

    if schema_type == 'integer':
        return 1

    if schema_type == 'number':
        return 1.0

    if schema_type == 'boolean':
        return True

    return None



class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle datetime and other special objects.
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()  # Convert datetime to ISO 8601 string format
        return super().default(obj)


def save_schema_example_as_json(schema_name, example_data, output_dir):
    """Save each generated example as a JSON file."""
    file_path = os.path.join(output_dir, f"{schema_name}.json")
    with open(file_path, 'w') as json_file:
        json.dump(example_data, json_file, indent=4, cls=CustomJSONEncoder)  # Use custom encoder
    print(f"✅ Example for '{schema_name}' saved to {file_path}")


def build_execution_tree(schema_name, schema, schemas, depth=0, seen_schemas=None):
    """
    Build a text-based tree view of schema dependencies.
    """
    if seen_schemas is None:
        seen_schemas = set()

    tree = "  " * depth + f"- {schema_name}\n"

    # Prevent infinite recursion
    if schema_name in seen_schemas and depth > 0:
        return "  " * depth + f"  (circular reference)\n"

    seen_schemas = seen_schemas.copy()
    seen_schemas.add(schema_name)

    if '$ref' in schema:
        ref_path = schema['$ref'].split('/')

        # Handle property-level references
        if len(ref_path) > 3 and ref_path[-2] == 'properties':
            schema_name = ref_path[-3]
            property_name = ref_path[-1]
            tree += "  " * (depth + 1) + f"(property ref: {schema_name}.{property_name})\n"
            ref_schema = schemas.get(schema_name, {})
            property_schema = ref_schema.get('properties', {}).get(property_name, {})
            if property_schema:
                return tree + build_execution_tree(f"{schema_name}.{property_name}", property_schema, schemas, depth + 1, seen_schemas)
            return tree

        # Handle normal schema-level references
        ref_name = ref_path[-1]
        tree += build_execution_tree(ref_name, schemas.get(ref_name, {}), schemas, depth + 1, seen_schemas)
        return tree

    # Handle allOf
    if 'allOf' in schema:
        for idx, sub_schema in enumerate(schema['allOf']):
            if '$ref' in sub_schema:
                ref_name = sub_schema['$ref'].split('/')[-1]
                tree += "  " * (depth + 1) + f"allOf[{idx}] → {ref_name}\n"
                tree += build_execution_tree(ref_name, schemas.get(ref_name, {}), schemas, depth + 2, seen_schemas)
            elif 'type' in sub_schema and sub_schema['type'] == 'object':
                tree += "  " * (depth + 1) + f"allOf[{idx}] (inline object)\n"
                for prop_name, prop_schema in sub_schema.get('properties', {}).items():
                    if '$ref' in prop_schema:
                        ref_name = prop_schema['$ref'].split('/')[-1]
                        tree += "  " * (depth + 2) + f"↳ {prop_name} → {ref_name}\n"
                        tree += build_execution_tree(ref_name, schemas.get(ref_name, {}), schemas, depth + 3, seen_schemas)
                    else:
                        tree += "  " * (depth + 2) + f"• {prop_name}\n"

    # Handle oneOf
    if 'oneOf' in schema:
        for idx, sub_schema in enumerate(schema['oneOf']):
            if '$ref' in sub_schema:
                ref_name = sub_schema['$ref'].split('/')[-1]
                tree += "  " * (depth + 1) + f"oneOf[{idx}] → {ref_name}\n"
                tree += build_execution_tree(ref_name, schemas.get(ref_name, {}), schemas, depth + 2, seen_schemas)

    # Handle anyOf
    if 'anyOf' in schema:
        for idx, sub_schema in enumerate(schema['anyOf']):
            if '$ref' in sub_schema:
                ref_name = sub_schema['$ref'].split('/')[-1]
                tree += "  " * (depth + 1) + f"anyOf[{idx}] → {ref_name}\n"
                tree += build_execution_tree(ref_name, schemas.get(ref_name, {}), schemas, depth + 2, seen_schemas)

    if schema.get('type') == 'object':
        for prop_name, prop_schema in schema.get('properties', {}).items():
            if '$ref' in prop_schema:
                ref_name = prop_schema['$ref'].split('/')[-1]
                tree += "  " * (depth + 1) + f"↳ {prop_name} → {ref_name}\n"
                tree += build_execution_tree(ref_name, schemas.get(ref_name, {}), schemas, depth + 2, seen_schemas)
            else:
                tree += "  " * (depth + 1) + f"• {prop_name}\n"

    elif schema.get('type') == 'array' and 'items' in schema:
        item_schema = schema['items']
        if '$ref' in item_schema:
            ref_name = item_schema['$ref'].split('/')[-1]
            tree += "  " * (depth + 1) + f"[ ] → {ref_name}\n"
            tree += build_execution_tree(ref_name, schemas.get(ref_name, {}), schemas, depth + 2, seen_schemas)

    return tree

def extract_and_save_schema_examples(openapi_file, output_dir):
    """Main entry point — extract endpoints and organize examples by endpoint/body/response/related."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    openapi_definition = load_openapi_definition(openapi_file)
    schemas = extract_schemas(openapi_definition)

    if not schemas:
        print("No schemas found.")
        return

    print("\n=== Extracting Endpoints and Organizing Examples ===\n")

    # Extract endpoints
    endpoints = extract_endpoints_from_openapi(openapi_definition)

    print(f"Found {len(endpoints)} endpoints\n")

    # Process each endpoint
    for endpoint in endpoints:
        endpoint_name = endpoint['name']
        print(f"\n📁 Processing endpoint: {endpoint_name}")
        print(f"   {endpoint['method'].upper()} {endpoint['path']}")

        # Create endpoint directory
        endpoint_dir = os.path.join(output_dir, endpoint_name)
        os.makedirs(endpoint_dir, exist_ok=True)

        # Process request body
        if endpoint['requestSchema']:
            request_schema = endpoint['requestSchema']
            print(f"   📄 Request body: {request_schema}")

            # Create body directory
            body_dir = os.path.join(endpoint_dir, 'body')
            os.makedirs(body_dir, exist_ok=True)

            # Generate and save main schema
            schema_data = schemas.get(request_schema, {})
            example = generate_example_from_schema(schema_data, schemas)
            main_file = os.path.join(body_dir, f"{request_schema}.json")
            with open(main_file, 'w') as f:
                json.dump(example, f, indent=4, cls=CustomJSONEncoder)
            print(f"      ✅ {request_schema}.json")

            # Get all dependencies
            dependencies = get_schema_dependencies(request_schema, schemas)
            dependencies.discard(request_schema)  # Remove main schema

            if dependencies:
                # Create related directory
                related_dir = os.path.join(body_dir, 'related')
                os.makedirs(related_dir, exist_ok=True)

                # Generate and save related schemas
                for dep_schema in sorted(dependencies):
                    dep_data = schemas.get(dep_schema, {})
                    dep_example = generate_example_from_schema(dep_data, schemas)
                    dep_file = os.path.join(related_dir, f"{dep_schema}.json")
                    with open(dep_file, 'w') as f:
                        json.dump(dep_example, f, indent=4, cls=CustomJSONEncoder)

                print(f"      ✅ {len(dependencies)} related schemas in related/")

        # Process response schemas
        if endpoint['responseSchemas']:
            for response_schema in endpoint['responseSchemas']:
                print(f"   📄 Response: {response_schema}")

                # Create response directory
                response_dir = os.path.join(endpoint_dir, 'response')
                os.makedirs(response_dir, exist_ok=True)

                # Generate and save main response schema
                schema_data = schemas.get(response_schema, {})
                example = generate_example_from_schema(schema_data, schemas)
                main_file = os.path.join(response_dir, f"{response_schema}.json")
                with open(main_file, 'w') as f:
                    json.dump(example, f, indent=4, cls=CustomJSONEncoder)
                print(f"      ✅ {response_schema}.json")

                # Get all dependencies
                dependencies = get_schema_dependencies(response_schema, schemas)
                dependencies.discard(response_schema)  # Remove main schema

                if dependencies:
                    # Create related directory
                    related_dir = os.path.join(response_dir, 'related')
                    os.makedirs(related_dir, exist_ok=True)

                    # Generate and save related schemas
                    for dep_schema in sorted(dependencies):
                        dep_data = schemas.get(dep_schema, {})
                        dep_example = generate_example_from_schema(dep_data, schemas)
                        dep_file = os.path.join(related_dir, f"{dep_schema}.json")
                        with open(dep_file, 'w') as f:
                            json.dump(dep_example, f, indent=4, cls=CustomJSONEncoder)

                    print(f"      ✅ {len(dependencies)} related schemas in related/")

    print(f"\n✅ Examples organized by {len(endpoints)} endpoints")


if __name__ == '__main__':
    openapi_file_path = '../openapi.yaml'  # Your OpenAPI definition file
    output_directory = 'examples'       # Folder for generated examples
    extract_and_save_schema_examples(openapi_file_path, output_directory)





