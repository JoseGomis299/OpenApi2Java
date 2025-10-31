import json
import yaml
import os
from datetime import datetime


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
    """Main entry point — extract, expand, and save examples."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    openapi_definition = load_openapi_definition(openapi_file)
    schemas = extract_schemas(openapi_definition)

    if not schemas:
        print("No schemas found.")
        return

    print("\n=== Building Execution Trees and Examples ===\n")
    for schema_name, schema_data in schemas.items():
        # Show execution tree
        print(f"Schema: {schema_name}")
        print(build_execution_tree(schema_name, schema_data, schemas))
        print("-" * 60)

        # Generate full example with all refs expanded
        example = generate_example_from_schema(schema_data, schemas)
        save_schema_example_as_json(schema_name, example, output_dir)


if __name__ == '__main__':
    openapi_file_path = 'openapi.yaml'  # Your OpenAPI definition file
    output_directory = 'examples'       # Folder for generated examples
    extract_and_save_schema_examples(openapi_file_path, output_directory)





