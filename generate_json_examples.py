import json
import yaml
import os
from datetime import datetime


def extract_endpoints_from_openapi(openapi_definition):
    endpoints = []
    paths = openapi_definition.get('paths', {})

    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method not in ['get', 'post', 'put', 'patch', 'delete']:
                continue

            endpoint_parts = [p for p in path.split('/') if p and not p.startswith('{')]
            endpoint_name = f"{method.upper()}_{'_'.join(endpoint_parts)}" if endpoint_parts else f"{method.upper()}_root"

            request_schema = None
            request_body = operation.get('requestBody', {})
            if request_body:
                schema = request_body.get('content', {}).get('application/json', {}).get('schema', {})
                if '$ref' in schema:
                    request_schema = schema['$ref'].split('/')[-1]

            response_schemas = []
            responses = operation.get('responses', {})
            responses_comp = openapi_definition.get('components', {}).get('responses', {})

            for status_code, response in responses.items():
                if status_code.startswith('2'):
                    if '$ref' in response:
                        ref_name = response['$ref'].split('/')[-1]
                        if ref_name in responses_comp:
                            schema = responses_comp[ref_name].get('content', {}).get('application/json', {}).get('schema', {})
                            if '$ref' in schema:
                                response_schemas.append(schema['$ref'].split('/')[-1])
                    else:
                        schema = response.get('content', {}).get('application/json', {}).get('schema', {})
                        if '$ref' in schema:
                            response_schemas.append(schema['$ref'].split('/')[-1])

            endpoints.append({
                'name': endpoint_name,
                'path': path,
                'method': method,
                'requestSchema': request_schema,
                'responseSchemas': response_schemas
            })

    return endpoints


def get_schema_dependencies(schema_name, schemas, visited=None):
    if visited is None:
        visited = set()

    if schema_name in visited or schema_name not in schemas:
        return visited

    visited.add(schema_name)
    schema = schemas[schema_name]

    if 'allOf' in schema:
        for sub_schema in schema['allOf']:
            if '$ref' in sub_schema:
                get_schema_dependencies(sub_schema['$ref'].split('/')[-1], schemas, visited)
            elif isinstance(sub_schema, dict) and 'properties' in sub_schema:
                extract_refs_from_properties(sub_schema.get('properties', {}), schemas, visited)

    if 'oneOf' in schema:
        for sub_schema in schema['oneOf']:
            if '$ref' in sub_schema:
                get_schema_dependencies(sub_schema['$ref'].split('/')[-1], schemas, visited)

    if 'anyOf' in schema:
        for sub_schema in schema['anyOf']:
            if '$ref' in sub_schema:
                get_schema_dependencies(sub_schema['$ref'].split('/')[-1], schemas, visited)

    if 'properties' in schema:
        extract_refs_from_properties(schema['properties'], schemas, visited)

    return visited


def extract_refs_from_properties(properties, schemas, visited):
    for prop_schema in properties.values():
        if '$ref' in prop_schema:
            get_schema_dependencies(prop_schema['$ref'].split('/')[-1], schemas, visited)

        if prop_schema.get('type') == 'array' and 'items' in prop_schema and '$ref' in prop_schema['items']:
            get_schema_dependencies(prop_schema['items']['$ref'].split('/')[-1], schemas, visited)

        for key in ['oneOf', 'anyOf', 'allOf']:
            if key in prop_schema:
                for sub_schema in prop_schema[key]:
                    if '$ref' in sub_schema:
                        get_schema_dependencies(sub_schema['$ref'].split('/')[-1], schemas, visited)


def load_openapi_definition(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        if file_path.endswith('.json'):
            return json.load(file)
        return yaml.safe_load(file)


def extract_schemas(openapi_definition):
    return openapi_definition.get('components', {}).get('schemas', {})


def generate_example_from_schema(schema, schemas, seen_refs=None):
    if seen_refs is None:
        seen_refs = set()

    if not schema:
        return None

    if '$ref' in schema:
        ref_path = schema['$ref'].split('/')
        if len(ref_path) > 3 and ref_path[-2] == 'properties':
            schema_name = ref_path[-3]
            property_name = ref_path[-1]
            property_schema = schemas.get(schema_name, {}).get('properties', {}).get(property_name, {})
            if property_schema:
                return generate_example_from_schema(property_schema, schemas, seen_refs)

        ref_name = ref_path[-1]
        if ref_name in seen_refs:
            return f"# circular reference to {ref_name}"
        seen_refs.add(ref_name)
        return generate_example_from_schema(schemas.get(ref_name, {}), schemas, seen_refs)

    if 'allOf' in schema:
        if len(schema['allOf']) == 1:
            return generate_example_from_schema(schema['allOf'][0], schemas, seen_refs.copy())

        merged_example = {}
        for sub_schema in schema['allOf']:
            sub_example = generate_example_from_schema(sub_schema, schemas, seen_refs.copy())
            if isinstance(sub_example, dict):
                merged_example.update(sub_example)
            elif sub_example is not None:
                return sub_example
        return merged_example

    if 'oneOf' in schema and schema['oneOf']:
        return generate_example_from_schema(schema['oneOf'][0], schemas, seen_refs.copy())

    if 'anyOf' in schema and schema['anyOf']:
        return generate_example_from_schema(schema['anyOf'][0], schemas, seen_refs.copy())

    for key in ['example', 'default']:
        if key in schema:
            return schema[key]

    if 'enum' in schema:
        return schema['enum'][0]

    schema_type = schema.get('type', 'object')

    if schema_type == 'object':
        return {prop_name: generate_example_from_schema(prop_schema, schemas, seen_refs.copy())
                for prop_name, prop_schema in schema.get('properties', {}).items()}

    if schema_type == 'array':
        return [generate_example_from_schema(schema.get('items', {}), schemas, seen_refs.copy())]

    if schema_type == 'string':
        fmt = schema.get('format', '')
        return {'date-time': "2025-01-01T00:00:00Z", 'date': "2025-01-01",
                'email': "user@example.com", 'uuid': "123e4567-e89b-12d3-a456-426614174000"
               }.get(fmt, "example_string")

    if schema_type == 'integer':
        return 1
    if schema_type == 'number':
        return 1.0
    if schema_type == 'boolean':
        return True

    return None


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def extract_and_save_schema_examples(openapi_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    openapi_definition = load_openapi_definition(openapi_file)
    schemas = extract_schemas(openapi_definition)

    if not schemas:
        print("No schemas found.")
        return

    print("\n=== Extracting Endpoints and Organizing Examples ===\n")

    endpoints = extract_endpoints_from_openapi(openapi_definition)
    print(f"Found {len(endpoints)} endpoints\n")

    for endpoint in endpoints:
        print(f"\n📁 Processing endpoint: {endpoint['name']}")
        print(f"   {endpoint['method'].upper()} {endpoint['path']}")

        endpoint_dir = os.path.join(output_dir, endpoint['name'])

        if endpoint['requestSchema']:
            print(f"   📄 Request body: {endpoint['requestSchema']}")
            process_schema(endpoint['requestSchema'], schemas, endpoint_dir, 'body')

        for response_schema in endpoint['responseSchemas']:
            print(f"   📄 Response: {response_schema}")
            process_schema(response_schema, schemas, endpoint_dir, 'response')

    print(f"\n✅ Examples organized by {len(endpoints)} endpoints")


def process_schema(schema_name, schemas, endpoint_dir, folder_name):
    folder_dir = os.path.join(endpoint_dir, folder_name)
    os.makedirs(folder_dir, exist_ok=True)

    schema_data = schemas.get(schema_name, {})
    example = generate_example_from_schema(schema_data, schemas)

    with open(os.path.join(folder_dir, f"{schema_name}.json"), 'w', encoding='utf-8') as f:
        json.dump(example, f, indent=4, cls=CustomJSONEncoder)
    print(f"      ✅ {schema_name}.json")

    dependencies = get_schema_dependencies(schema_name, schemas)
    dependencies.discard(schema_name)

    if dependencies:
        related_dir = os.path.join(folder_dir, 'related')
        os.makedirs(related_dir, exist_ok=True)

        for dep_schema in sorted(dependencies):
            dep_example = generate_example_from_schema(schemas.get(dep_schema, {}), schemas)
            with open(os.path.join(related_dir, f"{dep_schema}.json"), 'w', encoding='utf-8') as f:
                json.dump(dep_example, f, indent=4, cls=CustomJSONEncoder)

        print(f"      ✅ {len(dependencies)} related schemas in related/")


def generate_all_schemas_folder(openapi_file, output_folder):
    """Generate ALL_SCHEMAS folder with unique schemas organized by inheritance."""
    with open(openapi_file, 'r', encoding='utf-8') as f:
        openapi_definition = yaml.safe_load(f)

    schemas = openapi_definition.get('components', {}).get('schemas', {})
    if not schemas:
        return

    all_schemas_dir = os.path.join(output_folder, 'ALL_SCHEMAS')
    if os.path.exists(all_schemas_dir):
        import shutil
        shutil.rmtree(all_schemas_dir)
    os.makedirs(all_schemas_dir, exist_ok=True)

    print(f"\n📦 Generating ALL_SCHEMAS folder...")

    # Build inheritance map
    inheritance_map = {}
    for schema_name, schema_def in schemas.items():
        parent = None
        if 'allOf' in schema_def:
            for item in schema_def['allOf']:
                if '$ref' in item:
                    parent = item['$ref'].split('/')[-1]
                    break
        inheritance_map[schema_name] = parent

    # Organize schemas by inheritance hierarchy
    base_schemas = {name for name, parent in inheritance_map.items() if parent is None}

    # Generate base schemas at root level
    for schema_name in sorted(base_schemas):
        example = generate_example_from_schema(schemas[schema_name], schemas)
        file_path = os.path.join(all_schemas_dir, f"{schema_name}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(example, f, indent=4, cls=CustomJSONEncoder)

    print(f"   ✅ Generated {len(base_schemas)} base schemas")

    # Generate derived schemas in subdirectories
    for schema_name, parent in sorted(inheritance_map.items()):
        if parent:
            # Create subdirectory for parent if it doesn't exist
            parent_dir = os.path.join(all_schemas_dir, parent)
            os.makedirs(parent_dir, exist_ok=True)

            example = generate_example_from_schema(schemas[schema_name], schemas)
            file_path = os.path.join(parent_dir, f"{schema_name}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(example, f, indent=4, cls=CustomJSONEncoder)

    derived_count = sum(1 for parent in inheritance_map.values() if parent)
    if derived_count > 0:
        print(f"   ✅ Generated {derived_count} derived schemas organized by parent")

    print(f"   📁 Total schemas in ALL_SCHEMAS: {len(schemas)}")


if __name__ == '__main__':
    from config import get_config, get_openapi_definition_files

    config = get_config()
    base_examples_folder = config['json']['examples_folder']

    definition_files = get_openapi_definition_files()

    if not definition_files:
        print("❌ No OpenAPI definition files found!")
        exit(1)

    print(f"🚀 Generating JSON examples from {len(definition_files)} definition(s)...\n")

    for name, file_path in definition_files:
        # Create subdirectory for this definition
        output_folder = os.path.join(base_examples_folder, name)
        print(f"\n{'='*60}")
        print(f"📋 Processing: {name} ({file_path})")
        print(f"{'='*60}")

        extract_and_save_schema_examples(file_path, output_folder)

        # Generate ALL_SCHEMAS folder
        generate_all_schemas_folder(file_path, output_folder)

    print(f"\n{'='*60}")
    print(f"✅ All JSON examples generated successfully!")
    print(f"{'='*60}")

