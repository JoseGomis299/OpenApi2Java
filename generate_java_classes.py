import os
import subprocess
import json
import re
import yaml


# Global dictionary to track all classes and their fields for inheritance detection
all_classes_fields = {}
# Global dictionary to track inheritance from OpenAPI allOf patterns
inheritance_map = {}
# Global dictionary to track oneOf fields that should use generics: {ClassName: {fieldName: [Type1, Type2, ...]}}
oneof_fields_map = {}


def to_java_class_name(name):
    """Convert a name to Java class name (PascalCase) - preserve existing casing."""
    # Remove file extension if present
    if name.endswith('.json'):
        name = name[:-5]

    # If the name already looks like PascalCase (starts with uppercase, no spaces/special chars)
    if re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
        return name

    # If it's camelCase (starts with lowercase), just capitalize the first letter
    if re.match(r'^[a-z][a-zA-Z0-9]*$', name):
        return name[0].upper() + name[1:]

    # Otherwise, convert to PascalCase by splitting and capitalizing
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    parts = re.split(r'[_\s-]+', name)
    return ''.join(word.capitalize() for word in parts if word)


def to_java_field_name(name):
    """Convert a name to Java field name (camelCase) - preserve existing camelCase."""
    # If the name already looks like camelCase, keep it
    if re.match(r'^[a-z][a-zA-Z0-9]*$', name):
        return name

    # Remove special characters but preserve word boundaries
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    parts = re.split(r'[_\s-]+', name)
    if not parts:
        return name
    return parts[0].lower() + ''.join(word.capitalize() for word in parts[1:] if word)


def detect_base_class(class_name, fields):
    """
    Detect if this class should extend a base class.
    Only uses inheritance_map from OpenAPI allOf patterns.
    No naming conventions - purely based on OpenAPI structure.
    """

    # Check if we have inheritance info from OpenAPI schema
    if class_name in inheritance_map:
        base_class = inheritance_map[class_name]
        if base_class and base_class != class_name:
            return base_class

    # No fallback - only use explicit allOf relationships from OpenAPI
    return None


def load_openapi_inheritance(openapi_file='openapi.yaml'):
    """
    Load OpenAPI schema and extract inheritance relationships from allOf patterns.
    Populates the inheritance_map global dictionary.
    Detects inheritance when:
    - Schema uses allOf
    - First element of allOf is a $ref to another schema
    No naming conventions required - purely based on OpenAPI structure.
    """
    global inheritance_map

    try:
        with open(openapi_file, 'r') as f:
            openapi_spec = yaml.safe_load(f)

        schemas = openapi_spec.get('components', {}).get('schemas', {})

        for schema_name, schema_def in schemas.items():
            class_name = to_java_class_name(schema_name)

            # Check if schema uses allOf
            if isinstance(schema_def, dict) and 'allOf' in schema_def:
                allof_list = schema_def['allOf']

                # Only consider the FIRST element of allOf for inheritance
                if allof_list and len(allof_list) > 0:
                    first_element = allof_list[0]

                    if isinstance(first_element, dict) and '$ref' in first_element:
                        ref_path = first_element['$ref']
                        # Extract the schema name from the reference
                        if ref_path.startswith('#/components/schemas/'):
                            base_schema_name = ref_path.split('/')[-1]
                            base_class_name = to_java_class_name(base_schema_name)

                            # No naming restrictions - any $ref in allOf creates inheritance
                            inheritance_map[class_name] = base_class_name
                            print(f"  📋 Detected: {class_name} extends {base_class_name} (from OpenAPI)")

        print(f"\n  Found {len(inheritance_map)} inheritance relationships from OpenAPI schema\n")

    except FileNotFoundError:
        print(f"  ⚠️  OpenAPI file '{openapi_file}' not found, skipping schema-based inheritance detection\n")
    except Exception as e:
        print(f"  ⚠️  Error loading OpenAPI schema: {e}\n")


def load_openapi_oneof_fields(openapi_file='openapi.yaml'):
    """
    Load OpenAPI schema and extract oneOf field definitions.
    Populates the oneof_fields_map global dictionary.
    For fields using oneOf, we'll generate a base class and use generics in Java.

    oneof_fields_map structure:
    {
        'ClassName': {
            'fieldName': {
                'types': [Type1, Type2, ...],
                'baseClass': 'BaseClassName'
            }
        }
    }
    """
    global oneof_fields_map, inheritance_map

    try:
        with open(openapi_file, 'r') as f:
            openapi_spec = yaml.safe_load(f)

        schemas = openapi_spec.get('components', {}).get('schemas', {})

        for schema_name, schema_def in schemas.items():
            class_name = to_java_class_name(schema_name)

            # Navigate through the schema to find oneOf fields
            # Collect all properties from different sources
            all_properties = {}

            # Handle direct properties
            if isinstance(schema_def, dict) and 'properties' in schema_def:
                all_properties.update(schema_def['properties'])

            # Handle allOf with properties - merge all properties from all allOf elements
            if isinstance(schema_def, dict) and 'allOf' in schema_def:
                for item in schema_def['allOf']:
                    if isinstance(item, dict) and 'properties' in item:
                        all_properties.update(item['properties'])

            # Now check all collected properties for oneOf fields
            if all_properties:
                for field_name, field_def in all_properties.items():
                    if isinstance(field_def, dict) and 'oneOf' in field_def:
                        # Extract the types from oneOf
                        oneof_types = []
                        for ref_item in field_def['oneOf']:
                            if isinstance(ref_item, dict) and '$ref' in ref_item:
                                ref_path = ref_item['$ref']
                                if ref_path.startswith('#/components/schemas/'):
                                    type_name = ref_path.split('/')[-1]
                                    java_type = to_java_class_name(type_name)
                                    oneof_types.append(java_type)

                        if oneof_types:
                            # Use the field name itself as the base class (without "Base" suffix)
                            # This handles cases where the JSON generator creates a concrete class
                            # from the first oneOf option using the field name
                            base_class_name = to_java_class_name(field_name)

                            if class_name not in oneof_fields_map:
                                oneof_fields_map[class_name] = {}

                            oneof_fields_map[class_name][field_name] = {
                                'types': oneof_types,
                                'baseClass': base_class_name
                            }

                            # Add inheritance relationships for all oneOf types to extend the base class
                            for java_type in oneof_types:
                                # Only add if not already inheriting from something else
                                if java_type not in inheritance_map:
                                    inheritance_map[java_type] = base_class_name

                            print(f"  🔀 Detected: {class_name}.{field_name} uses oneOf with {len(oneof_types)} types")
                            print(f"     → Using {base_class_name} as base class (will be generated as abstract)")

        if oneof_fields_map:
            total_fields = sum(len(fields) for fields in oneof_fields_map.values())
            print(f"\n  Found {total_fields} oneOf fields across {len(oneof_fields_map)} classes\n")
        else:
            print("  No oneOf fields found\n")

    except FileNotFoundError:
        print(f"  ⚠️  OpenAPI file '{openapi_file}' not found, skipping oneOf detection\n")
    except Exception as e:
        print(f"  ⚠️  Error loading OpenAPI schema for oneOf: {e}\n")


def get_inherited_and_new_fields(class_name, all_fields, base_class_name):
    """
    Separate fields into inherited and new fields.
    Returns: (inherited_fields, new_fields)
    """
    if not base_class_name or base_class_name not in all_classes_fields:
        return ([], all_fields)

    base_fields = set(all_classes_fields[base_class_name])
    inherited = []
    new_fields = []

    for field_name, field_type in all_fields:
        if field_name in base_fields:
            inherited.append((field_name, field_type))
        else:
            new_fields.append((field_name, field_type))

    return (inherited, new_fields)


def generate_base_class_for_oneof(base_class_name, package="com.mapfre.home.model"):
    """
    Generate an empty abstract base class for oneOf polymorphic fields.
    This serves as a marker interface/base class that all oneOf types will extend.
    Note: This class may have the same name as a field in the OpenAPI schema,
    but it represents the polymorphic base type, not a concrete implementation.
    """
    java_code = f"package {package};\n\n"
    java_code += "import lombok.Data;\n"
    java_code += "import lombok.NoArgsConstructor;\n"
    java_code += "import lombok.AllArgsConstructor;\n\n"
    java_code += "@Data\n"
    java_code += "@NoArgsConstructor\n"
    java_code += "@AllArgsConstructor\n"
    java_code += f"public abstract class {base_class_name} {{\n"
    java_code += "    // Polymorphic base class for oneOf types\n"
    java_code += "    // All concrete implementations will extend this class\n"
    java_code += "}\n"
    return java_code



def get_java_type(value, field_name=""):
    """Determine Java type from JSON value."""
    if value is None:
        return "Object"
    elif isinstance(value, bool):
        return "Boolean"
    elif isinstance(value, int):
        return "Integer" if abs(value) < 2147483647 else "Long"
    elif isinstance(value, float):
        return "Double"
    elif isinstance(value, str):
        # Check for date-time patterns
        if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', value):
            return "LocalDateTime"
        elif re.match(r'\d{4}-\d{2}-\d{2}', value):
            return "LocalDate"
        return "String"
    elif isinstance(value, list):
        if not value:
            return "List<Object>"
        # Infer type from first element
        item_type = get_java_type(value[0])
        return f"List<{item_type}>"
    elif isinstance(value, dict):
        # Create nested class name
        class_name = to_java_class_name(field_name) if field_name else "Object"
        return class_name
    return "Object"


def generate_java_class_manual(class_name, json_data, package="com.mapfre.home.model", output_dir=None):
    """Generate Java class code manually from JSON data."""
    global oneof_fields_map

    imports = set()
    imports.add("import lombok.Data;")
    imports.add("import lombok.Builder;")
    imports.add("import lombok.NoArgsConstructor;")
    imports.add("import lombok.AllArgsConstructor;")

    fields = []
    nested_classes = {}  # Track nested classes to avoid duplicates
    generic_params = []  # Track generic type parameters for class-level generics

    if not isinstance(json_data, dict):
        # Handle arrays at root level
        return None

    for field_name, value in json_data.items():
        java_field = to_java_field_name(field_name)

        # Check if this field is a oneOf field
        if class_name in oneof_fields_map and field_name in oneof_fields_map[class_name]:
            # Use generic type parameter instead of wildcard
            base_class = oneof_fields_map[class_name][field_name]['baseClass']
            # Create a generic parameter name from the field name
            generic_param_name = "T" + to_java_class_name(field_name)
            generic_params.append(f"{generic_param_name} extends {base_class}")
            java_type = generic_param_name
            # Add comment indicating the possible types
            oneof_types = oneof_fields_map[class_name][field_name]['types']
            types_comment = f"    // Can be one of: {', '.join(oneof_types)}"
            fields.append(types_comment)
        else:
            java_type, nested_class = get_java_type_with_nested(value, field_name, nested_classes)

        # Add imports based on type
        if "List" in java_type:
            imports.add("import java.util.List;")
        if "LocalDateTime" in java_type:
            imports.add("import java.time.LocalDateTime;")
        if "LocalDate" in java_type:
            imports.add("import java.time.LocalDate;")

        # Generate field without @JsonProperty annotation
        field_def = f'    private {java_type} {java_field};'
        fields.append(field_def)

    # Build the class
    java_code = f"package {package};\n\n"
    java_code += "\n".join(sorted(imports)) + "\n\n"
    java_code += "@Data\n"
    java_code += "@Builder\n"
    java_code += "@NoArgsConstructor\n"
    java_code += "@AllArgsConstructor\n"

    # Add generic parameters if any oneOf fields exist
    if generic_params:
        generic_declaration = f"<{', '.join(generic_params)}>"
        java_code += f"public class {class_name}{generic_declaration} {{\n\n"
    else:
        java_code += f"public class {class_name} {{\n\n"

    java_code += "\n".join(fields)
    java_code += "\n}\n"

    # Generate separate files for nested classes
    if nested_classes and output_dir:
        for nested_name, nested_data in nested_classes.items():
            generate_nested_class_file(nested_name, nested_data, package, output_dir)

    return java_code


def generate_java_class_with_inheritance(class_name, json_data, base_class_name=None, package="com.mapfre.home.model", output_dir=None):
    """Generate Java class code with inheritance support."""
    global oneof_fields_map

    imports = set()
    imports.add("import lombok.Data;")
    imports.add("import lombok.NoArgsConstructor;")
    imports.add("import lombok.AllArgsConstructor;")

    # Use @EqualsAndHashCode(callSuper=true) if extending a class
    if base_class_name:
        imports.add("import lombok.EqualsAndHashCode;")
        imports.add("import lombok.Builder;")
    else:
        imports.add("import lombok.Builder;")

    fields = []
    nested_classes = {}
    generic_params = []  # Track generic type parameters for class-level generics

    if not isinstance(json_data, dict):
        return None

    # Collect all fields with their types
    all_field_info = []
    for field_name, value in json_data.items():
        java_field = to_java_field_name(field_name)

        # Check if this field is a oneOf field
        if class_name in oneof_fields_map and field_name in oneof_fields_map[class_name]:
            # Use generic type parameter instead of wildcard
            base_class = oneof_fields_map[class_name][field_name]['baseClass']
            # Create a generic parameter name from the field name
            generic_param_name = "T" + to_java_class_name(field_name)
            generic_params.append(f"{generic_param_name} extends {base_class}")
            java_type = generic_param_name
        else:
            java_type, nested_class = get_java_type_with_nested(value, field_name, nested_classes)

        all_field_info.append((field_name, java_field, java_type))

        # Add imports based on type
        if "List" in java_type:
            imports.add("import java.util.List;")
        if "LocalDateTime" in java_type:
            imports.add("import java.time.LocalDateTime;")
        if "LocalDate" in java_type:
            imports.add("import java.time.LocalDate;")

    # If there's a base class, filter out inherited fields
    if base_class_name and base_class_name in all_classes_fields:
        base_field_names = set(all_classes_fields[base_class_name])
        for orig_name, java_field, java_type in all_field_info:
            if orig_name not in base_field_names:
                # Add comment for oneOf fields
                if class_name in oneof_fields_map and orig_name in oneof_fields_map[class_name]:
                    oneof_types = oneof_fields_map[class_name][orig_name]['types']
                    types_comment = f"    // Can be one of: {', '.join(oneof_types)}"
                    fields.append(types_comment)
                field_def = f'    private {java_type} {java_field};'
                fields.append(field_def)
    else:
        for orig_name, java_field, java_type in all_field_info:
            # Add comment for oneOf fields
            if class_name in oneof_fields_map and orig_name in oneof_fields_map[class_name]:
                oneof_types = oneof_fields_map[class_name][orig_name]['types']
                types_comment = f"    // Can be one of: {', '.join(oneof_types)}"
                fields.append(types_comment)
            field_def = f'    private {java_type} {java_field};'
            fields.append(field_def)

    # Build the class
    java_code = f"package {package};\n\n"
    java_code += "\n".join(sorted(imports)) + "\n\n"
    java_code += "@Data\n"

    if base_class_name:
        java_code += "@EqualsAndHashCode(callSuper = true)\n"

    java_code += "@NoArgsConstructor\n"
    java_code += "@AllArgsConstructor\n"

    # Add extends clause if there's a base class
    # Add generic parameters if any oneOf fields exist
    generic_declaration = f"<{', '.join(generic_params)}>" if generic_params else ""

    if base_class_name:
        java_code += f"public class {class_name}{generic_declaration} extends {base_class_name} {{\n\n"
    else:
        java_code += "@Builder\n"
        java_code += f"public class {class_name}{generic_declaration} {{\n\n"

    if fields:
        java_code += "\n".join(fields)
    else:
        java_code += "    // All fields inherited from " + base_class_name if base_class_name else "    // No fields"

    java_code += "\n}\n"

    # Generate separate files for nested classes
    if nested_classes and output_dir:
        for nested_name, nested_data in nested_classes.items():
            generate_nested_class_file(nested_name, nested_data, package, output_dir)

    return java_code



def get_java_type_with_nested(value, field_name, nested_classes_dict):
    """
    Determine Java type from JSON value and collect nested class definitions.
    Returns: (java_type_string, nested_class_data_or_none)
    """
    if value is None:
        return ("String", None)  # Default to String for null values
    elif isinstance(value, bool):
        return ("Boolean", None)
    elif isinstance(value, int):
        return ("Long", None)  # Use Long to handle all integer sizes
    elif isinstance(value, float):
        return ("Double", None)
    elif isinstance(value, str):
        # Check for date-time patterns
        if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', value):
            return ("LocalDateTime", None)
        elif re.match(r'\d{4}-\d{2}-\d{2}', value):
            return ("LocalDate", None)
        return ("String", None)
    elif isinstance(value, list):
        if not value:
            return ("List<Object>", None)
        # Infer type from first element
        first_item = value[0]
        if isinstance(first_item, dict):
            # Create nested class for list items - singularize the field name
            singular_name = field_name.rstrip('s') if field_name.endswith('s') else field_name
            # Preserve the original casing pattern
            nested_class_name = to_java_class_name(singular_name)
            nested_classes_dict[nested_class_name] = first_item
            return (f"List<{nested_class_name}>", None)
        else:
            item_type, _ = get_java_type_with_nested(first_item, field_name, nested_classes_dict)
            return (f"List<{item_type}>", None)
    elif isinstance(value, dict):
        # Create nested class - preserve original casing
        nested_class_name = to_java_class_name(field_name)
        nested_classes_dict[nested_class_name] = value
        return (nested_class_name, value)
    return ("Object", None)


def generate_nested_class(class_name, json_data):
    """Generate a nested Java class."""
    if not isinstance(json_data, dict):
        return ""

    fields = []
    inner_nested = {}

    for field_name, value in json_data.items():
        java_field = to_java_field_name(field_name)
        java_type, nested_data = get_java_type_with_nested(value, field_name, inner_nested)

        field_def = f'        private {java_type} {java_field};'
        fields.append(field_def)

    nested_code = "    @Data\n"
    nested_code += "    @Builder\n"
    nested_code += "    @NoArgsConstructor\n"
    nested_code += "    @AllArgsConstructor\n"
    nested_code += f"    public static class {class_name} {{\n\n"
    nested_code += "\n".join(fields)

    # Add deeply nested classes
    if inner_nested:
        nested_code += "\n\n"
        inner_code = []
        for inner_name, inner_data in inner_nested.items():
            inner_class = generate_deeply_nested_class(inner_name, inner_data)
            if inner_class:
                inner_code.append(inner_class)
        nested_code += "\n\n".join(inner_code)

    nested_code += "\n    }"

    return nested_code


def generate_nested_class_file(class_name, json_data, package, output_dir):
    """Generate a nested class as a separate file."""
    if not isinstance(json_data, dict):
        return

    imports = set()
    imports.add("import lombok.Data;")
    imports.add("import lombok.Builder;")
    imports.add("import lombok.NoArgsConstructor;")
    imports.add("import lombok.AllArgsConstructor;")

    fields = []
    inner_nested = {}

    for field_name, value in json_data.items():
        java_field = to_java_field_name(field_name)
        java_type, nested_data = get_java_type_with_nested(value, field_name, inner_nested)

        # Add imports based on type
        if "List" in java_type:
            imports.add("import java.util.List;")
        if "LocalDateTime" in java_type:
            imports.add("import java.time.LocalDateTime;")
        if "LocalDate" in java_type:
            imports.add("import java.time.LocalDate;")

        field_def = f'    private {java_type} {java_field};'
        fields.append(field_def)

    # Build the class
    java_code = f"package {package};\n\n"
    java_code += "\n".join(sorted(imports)) + "\n\n"
    java_code += "@Data\n"
    java_code += "@Builder\n"
    java_code += "@NoArgsConstructor\n"
    java_code += "@AllArgsConstructor\n"
    java_code += f"public class {class_name} {{\n\n"
    java_code += "\n".join(fields)
    java_code += "\n}\n"

    # Write to file
    output_file = os.path.join(output_dir, f"{class_name}.java")
    with open(output_file, 'w') as f:
        f.write(java_code)

    # Generate files for deeply nested classes
    if inner_nested:
        for inner_name, inner_data in inner_nested.items():
            generate_nested_class_file(inner_name, inner_data, package, output_dir)


def generate_deeply_nested_class(class_name, json_data):
    """Generate a deeply nested class (3rd level)."""
    if not isinstance(json_data, dict):
        return ""

    fields = []

    for field_name, value in json_data.items():
        java_field = to_java_field_name(field_name)
        java_type = get_java_type(value, field_name)

        field_def = f'            private {java_type} {java_field};'
        fields.append(field_def)

    nested_code = "        @Data\n"
    nested_code += "        @Builder\n"
    nested_code += "        @NoArgsConstructor\n"
    nested_code += "        @AllArgsConstructor\n"
    nested_code += f"        public static class {class_name} {{\n\n"
    nested_code += "\n".join(fields)
    nested_code += "\n        }"

    return nested_code


def convert_json_to_java(examples_dir, output_dir):
    """
    Convert JSON example files to Java classes using quicktype.
    Generates Spring-compatible POJOs with Lombok annotations.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get all JSON files from examples directory
    json_files = [f for f in os.listdir(examples_dir) if f.endswith('.json')]

    if not json_files:
        print("No JSON files found in examples directory.")
        return

    print(f"\n=== Converting {len(json_files)} JSON files to Java classes ===\n")

    for json_file in json_files:
        json_path = os.path.join(examples_dir, json_file)
        class_name = json_file.replace('.json', '')

        # Skip empty or invalid JSON files
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                if not data:
                    print(f"⚠️  Skipping {json_file} (empty)")
                    continue
        except json.JSONDecodeError as e:
            print(f"⚠️  Skipping {json_file} (invalid JSON: {e})")
            continue
        except Exception as e:
            print(f"⚠️  Skipping {json_file} (error: {e})")
            continue

        # Define output path for Java file
        output_file = os.path.join(output_dir, f"{class_name}.java")

        # Build quicktype command
        # Options:
        # --lang java: Generate Java code
        # --src: Source JSON file
        # --out: Output Java file
        # --package: Java package name
        # --lombok: Use Lombok annotations (@Data, @Builder, etc.)
        # --jackson: Use Jackson annotations for JSON serialization
        # --just-types: Only generate types, no additional code
        quicktype_cmd = [
            'quicktype',
            '--lang', 'java',
            '--src', json_path,
            '--out', output_file,
            '--package', 'com.mapfre.home.model',
            '--lombok',
            '--jackson',
            '--just-types'
        ]

        try:
            result = subprocess.run(
                quicktype_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ Generated {class_name}.java")

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to generate {class_name}.java")
            if e.stderr:
                print(f"   Error: {e.stderr.strip()}")
        except FileNotFoundError:
            print("❌ Error: quicktype is not installed.")
            print("   Install it with: npm install -g quicktype")
            return


def convert_all_to_single_package(examples_dir, output_dir):
    """
    Alternative approach: Convert all JSON files at once to a single package.
    This allows quicktype to better handle shared types and references.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get all JSON files
    json_files = [os.path.join(examples_dir, f) for f in os.listdir(examples_dir) if f.endswith('.json')]

    if not json_files:
        print("No JSON files found in examples directory.")
        return

    print(f"\n=== Converting all JSON files to Java package ===\n")

    # Build quicktype command with all files
    quicktype_cmd = [
        'quicktype',
        '--lang', 'java',
        '--src-lang', 'json',
        '--out', output_dir,
        '--package', 'com.mapfre.home.model',
        '--lombok',
        '--jackson',
        '--just-types',
        '--array-type', 'list'
    ] + json_files

    try:
        result = subprocess.run(
            quicktype_cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Count generated files
        java_files = [f for f in os.listdir(output_dir) if f.endswith('.java')]
        print(f"✅ Generated {len(java_files)} Java class files in {output_dir}")
        print(f"   Package: com.mapfre.home.model")

    except subprocess.CalledProcessError as e:
        print("❌ Failed to generate Java classes")
        if e.stderr:
            print(f"   Error: {e.stderr.strip()}")
    except FileNotFoundError:
        print("❌ Error: quicktype is not installed.")
        print("   Install it with: npm install -g quicktype")
        return


def check_quicktype_installed():
    """Check if quicktype is installed."""
    try:
        result = subprocess.run(
            ['quicktype', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ quicktype version: {result.stdout.strip()}\n")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_manually(examples_dir, output_dir, package="com.mapfre.home.model"):
    """
    Manually generate Java classes from JSON files without quicktype.
    This is a fallback method with inheritance detection.
    """
    global all_classes_fields

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    json_files = [f for f in os.listdir(examples_dir) if f.endswith('.json')]

    if not json_files:
        print("No JSON files found.")
        return

    print(f"\n=== Manually generating Java classes from {len(json_files)} JSON files ===\n")
    print("Pass 1: Analyzing class structures for inheritance...\n")

    # Load inheritance relationships from OpenAPI schema
    load_openapi_inheritance('openapi.yaml')

    # Load oneOf fields from OpenAPI schema
    load_openapi_oneof_fields('openapi.yaml')

    # First pass: collect all class structures
    class_data = {}
    for json_file in json_files:
        json_path = os.path.join(examples_dir, json_file)
        class_name = to_java_class_name(json_file.replace('.json', ''))

        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            if not isinstance(data, dict):
                continue

            # Collect field names
            field_names = list(data.keys())
            all_classes_fields[class_name] = field_names
            class_data[class_name] = (json_path, data)

        except Exception as e:
            continue

    print(f"Analyzed {len(all_classes_fields)} classes\n")

    # Generate base classes for oneOf fields
    print("Pass 1.5: Generating base classes for oneOf fields...\n")

    base_classes_generated = set()
    for class_name, field_map in oneof_fields_map.items():
        for field_name, field_info in field_map.items():
            base_class_name = field_info['baseClass']
            if base_class_name not in base_classes_generated:
                # Generate empty base class
                java_code = generate_base_class_for_oneof(base_class_name, package)
                output_file = os.path.join(output_dir, f"{base_class_name}.java")
                with open(output_file, 'w') as f:
                    f.write(java_code)
                print(f"✅ Generated base class {base_class_name}.java")
                base_classes_generated.add(base_class_name)

    if base_classes_generated:
        print(f"\n✅ Generated {len(base_classes_generated)} base classes for oneOf fields\n")

    print("Pass 2: Generating Java classes...\n")

    # Second pass: generate all classes (without inheritance initially)
    # Skip classes that are oneOf base classes (already generated as abstract)
    generated = 0
    for class_name, (json_path, data) in class_data.items():
        # Skip if this class is a oneOf base class (already generated as abstract empty class)
        if class_name in base_classes_generated:
            print(f"⏭️  Skipping {class_name}.java (oneOf base class already generated)")
            continue

        try:
            # Generate without inheritance first
            java_code = generate_java_class_manual(class_name, data, package, output_dir)

            if java_code:
                output_file = os.path.join(output_dir, f"{class_name}.java")
                with open(output_file, 'w') as f:
                    f.write(java_code)
                print(f"✅ Generated {class_name}.java")
                generated += 1
            else:
                print(f"⚠️  Skipping {class_name} (could not generate)")

        except Exception as e:
            print(f"❌ Failed to generate {class_name}.java: {e}")

    print(f"\n✅ Generated {generated} Java class files")

    # Third pass: Detect inheritance and regenerate classes that should extend base classes
    print("\nPass 3: Detecting inheritance and regenerating classes...\n")

    regenerated = 0
    for class_name, (json_path, data) in class_data.items():
        try:
            # Detect base class
            base_class = detect_base_class(class_name, all_classes_fields[class_name])

            if base_class:
                # Regenerate with inheritance
                java_code = generate_java_class_with_inheritance(
                    class_name, data, base_class, package, output_dir
                )

                if java_code:
                    output_file = os.path.join(output_dir, f"{class_name}.java")
                    with open(output_file, 'w') as f:
                        f.write(java_code)
                    print(f"🔄 Regenerated {class_name}.java (extends {base_class})")
                    regenerated += 1

        except Exception as e:
            print(f"❌ Failed to regenerate {class_name}.java: {e}")

    print(f"\n✅ Regenerated {regenerated} classes with inheritance")


if __name__ == '__main__':
    examples_directory = 'examples'
    output_directory = 'java'
    package_name = 'com.java'

    print("=== JSON to Java Class Generator ===\n")

    # Check if quicktype is installed
    has_quicktype = check_quicktype_installed()

    if not has_quicktype:
        print("❌ quicktype is not installed.")
        print("\nInstallation options:")
        print("  Option 1 (npm):  npm install -g quicktype")
        print("  Option 2 (yarn): yarn global add quicktype")
        print("  Option 3 (brew): brew install quicktype")
        print("\nFalling back to manual generation (basic support)...\n")
        convert_manually(examples_directory, output_directory, package_name)
    else:
        # Choose conversion method
        print("Select conversion method:")
        print("1. Use quicktype - individual files")
        print("2. Use quicktype - all files together (recommended)")
        print("3. Manual generation (basic, no quicktype)")

        choice = input("\nEnter choice (1, 2, or 3) [default: 2]: ").strip() or "2"

        if choice == "1":
            convert_json_to_java(examples_directory, output_directory)
        elif choice == "3":
            convert_manually(examples_directory, output_directory, package_name)
        else:
            convert_all_to_single_package(examples_directory, output_directory)

    print("\n✅ Java class generation complete!")
    print(f"   Output directory: {output_directory}")
    print(f"   Package: {package_name}")

