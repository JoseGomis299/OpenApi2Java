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
    Reads from organized structure: examples/ENDPOINT/body|response/[related/]*.json
    """
    global all_classes_fields

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Collect all JSON files recursively from organized structure
    json_files_data = []

    for root, dirs, files in os.walk(examples_dir):
        for filename in files:
            if filename.endswith('.json'):
                json_path = os.path.join(root, filename)
                json_files_data.append((filename, json_path))

    if not json_files_data:
        print("No JSON files found.")
        return

    print(f"\n=== Manually generating Java classes from {len(json_files_data)} JSON files ===\n")
    print("Pass 1: Analyzing class structures for inheritance...\n")

    # Load inheritance relationships from OpenAPI schema
    load_openapi_inheritance('../openapi.yaml')

    # Load oneOf fields from OpenAPI schema
    load_openapi_oneof_fields('../openapi.yaml')

    # First pass: collect all class structures
    class_data = {}
    seen_classes = set()  # Track classes we've already processed to avoid duplicates

    for json_file, json_path in json_files_data:
        class_name = to_java_class_name(json_file.replace('.json', ''))

        # Skip if we've already processed this class (from another endpoint)
        if class_name in seen_classes:
            continue

        seen_classes.add(class_name)

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

    # Fourth pass: Organize classes into folders by domain
    print("\nPass 4: Organizing classes into domain folders...\n")
    organize_classes_by_domain(output_dir, package)


def organize_classes_by_domain(output_dir, base_package):
    """Organize generated classes by OpenAPI endpoints with body/response/related structure."""
    import re
    import yaml

    print("  Analyzing OpenAPI endpoints...")

    # Load OpenAPI to get endpoints
    try:
        with open('../openapi.yaml', 'r') as f:
            openapi_spec = yaml.safe_load(f)
    except:
        print("  ⚠️  Could not load openapi.yaml")
        return

    # Analyze all generated Java files first
    class_info = {}

    for filename in os.listdir(output_dir):
        if not filename.endswith('.java'):
            continue

        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'r') as f:
            content = f.read()

        # Extract class name
        class_match = re.search(r'public\s+(?:abstract\s+)?class\s+(\w+)', content)
        if not class_match:
            continue

        class_name = class_match.group(1)

        # Extract extends
        extends_match = re.search(r'extends\s+(\w+)', content)
        extends = extends_match.group(1) if extends_match else None

        # Extract field types (references)
        references = set()
        for match in re.finditer(r'private\s+(?:List<)?(\w+)>?\s+\w+;', content):
            field_type = match.group(1)
            if field_type not in ['String', 'Integer', 'Long', 'Double', 'Boolean', 'LocalDate', 'LocalDateTime', 'Object']:
                references.add(field_type)

        # Extract generic bounds
        generic_match = re.search(r'class\s+\w+<\w+\s+extends\s+(\w+)>', content)
        if generic_match:
            references.add(generic_match.group(1))

        class_info[class_name] = {
            'file': filename,
            'extends': extends,
            'references': list(references),
            'children': []
        }

    # Build children relationships
    for class_name, info in class_info.items():
        if info['extends'] and info['extends'] in class_info:
            class_info[info['extends']]['children'].append(class_name)

    def get_all_dependencies(class_name, visited=None):
        """Recursively get ALL dependencies including polymorphic children."""
        if visited is None:
            visited = set()

        if class_name in visited or class_name not in class_info:
            return visited

        visited.add(class_name)
        info = class_info[class_name]

        # Include direct base class too (so bases are present for grouping)
        if info['extends']:
            get_all_dependencies(info['extends'], visited)

        # Add all field references
        for ref in info['references']:
            get_all_dependencies(ref, visited)

        # Add all children (polymorphic implementations)
        for child in info['children']:
            get_all_dependencies(child, visited)

        return visited

    def to_camel_case_folder(name: str) -> str:
        """Convert PascalCase to camelCase for folder names."""
        if not name:
            return name
        return name[0].lower() + name[1:]

    # Extract endpoints from OpenAPI
    endpoints_data = []
    paths = openapi_spec.get('paths', {})

    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method not in ['get', 'post', 'put', 'patch', 'delete']:
                continue

            # Generate endpoint name
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
                    request_schema = to_java_class_name(schema['$ref'].split('/')[-1])

            # Extract response schemas
            response_schemas = []
            responses = operation.get('responses', {})
            responses_comp = openapi_spec.get('components', {}).get('responses', {})

            for status_code, response in responses.items():
                if status_code.startswith('2'):
                    if '$ref' in response:
                        ref_name = response['$ref'].split('/')[-1]
                        if ref_name in responses_comp:
                            resp_content = responses_comp[ref_name].get('content', {})
                            json_content = resp_content.get('application/json', {})
                            schema = json_content.get('schema', {})
                            if '$ref' in schema:
                                response_schemas.append(to_java_class_name(schema['$ref'].split('/')[-1]))
                    else:
                        resp_content = response.get('content', {})
                        json_content = resp_content.get('application/json', {})
                        schema = json_content.get('schema', {})
                        if '$ref' in schema:
                            response_schemas.append(to_java_class_name(schema['$ref'].split('/')[-1]))

            endpoints_data.append({
                'name': endpoint_name,
                'request': request_schema,
                'responses': response_schemas
            })

    print(f"  Found {len(endpoints_data)} endpoints")

    # Collect all files to back up
    temp_files = {}
    for filename in os.listdir(output_dir):
        if filename.endswith('.java'):
            src = os.path.join(output_dir, filename)
            with open(src, 'r') as f:
                temp_files[filename] = f.read()

    # Also check subdirectories
    for root, dirs, files in os.walk(output_dir):
        for filename in files:
            if filename.endswith('.java'):
                filepath = os.path.join(root, filename)
                with open(filepath, 'r') as f:
                    temp_files[filename] = f.read()

    # Clear output directory
    import shutil
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        elif item.endswith('.java'):
            os.remove(item_path)

    # Helper: write dependencies into related grouped by inheritance
    def write_related_grouped(related_dir: str, dep_classes: set):
        os.makedirs(related_dir, exist_ok=True)
        written = set()

        # Build groups: base -> set(children)
        groups = {}
        for cls in dep_classes:
            if cls not in class_info:
                continue
            base = class_info[cls]['extends']
            if base:
                groups.setdefault(base, set()).add(cls)

        # Create subfolders for bases that have at least one child in deps
        for base, children in groups.items():
            subdir = os.path.join(related_dir, to_camel_case_folder(base))
            os.makedirs(subdir, exist_ok=True)
            # Write base itself (if available)
            if base in class_info:
                base_file = class_info[base]['file']
                if base_file in temp_files:
                    with open(os.path.join(subdir, base_file), 'w') as f:
                        f.write(temp_files[base_file])
                    written.add(base)
            # Write children
            for child in sorted(children):
                child_file = class_info[child]['file']
                if child_file in temp_files:
                    with open(os.path.join(subdir, child_file), 'w') as f:
                        f.write(temp_files[child_file])
                    written.add(child)

        # Write remaining classes (no inheritance grouping) into related root
        for cls in sorted(dep_classes):
            if cls in written or cls not in class_info:
                continue
            file = class_info[cls]['file']
            if file in temp_files:
                with open(os.path.join(related_dir, file), 'w') as f:
                    f.write(temp_files[file])
                written.add(cls)

        return len(written)

    # Organize files by endpoint
    total_files = 0

    for endpoint in endpoints_data:
        endpoint_dir = os.path.join(output_dir, endpoint['name'])

        # Process request body
        if endpoint['request'] and endpoint['request'] in class_info:
            body_dir = os.path.join(endpoint_dir, 'body')
            # Asegurarse de que endpoint_dir sea una cadena antes de usar os.path.join
            endpoint_dir = str(endpoint_dir)
            body_dir = os.path.join(endpoint_dir, 'body')
            os.makedirs(body_dir, exist_ok=True)

            # Save main class
            main_class = endpoint['request']
            main_file = class_info[main_class]['file']
            if main_file in temp_files:
                dest = os.path.join(body_dir, main_file)
                with open(dest, 'w') as f:
                    f.write(temp_files[main_file])
                total_files += 1
            else:
                print(f"⚠️  File '{main_file}' for class '{main_class}' not found.")

            # Get all dependencies including bases and children
            all_deps = get_all_dependencies(main_class)
            all_deps.discard(main_class)

            if all_deps:
                related_dir = os.path.join(body_dir, 'related')
                total_files += write_related_grouped(related_dir, all_deps)

        # Process responses
        for response_class in endpoint['responses']:
            if response_class not in class_info:
                continue

            response_dir = os.path.join(str(endpoint_dir), 'response')
            os.makedirs(response_dir, exist_ok=True)

            # Save main response class
            main_file = class_info[response_class]['file']
            if main_file in temp_files:
                dest = os.path.join(str(response_dir), main_file)
                with open(dest, 'w') as f:
                    f.write(temp_files[main_file])
                total_files += 1

            # Get all dependencies including bases and children
            all_deps = get_all_dependencies(response_class)
            all_deps.discard(response_class)

            if all_deps:
                related_dir = os.path.join(str(response_dir), 'related')
                total_files += write_related_grouped(str(related_dir), all_deps)

    print(f"✅ Organized {total_files} files into {len(endpoints_data)} endpoint folders")
    print(f"   Structure: endpoint/body|response/related/ (grouped by inheritance)\n")


def fix_imports_after_organization(output_dir, base_package, class_info):
    """Fix imports in all organized Java files."""
    print("Pass 4.5: Fixing imports in organized classes...\n")

    # Build map of class name -> package
    class_packages = {}
    for root, dirs, files in os.walk(output_dir):
        for filename in files:
            if not filename.endswith('.java'):
                continue

            class_name = filename[:-5]
            rel_path = os.path.relpath(root, output_dir)

            if rel_path == '.':
                class_packages[class_name] = base_package
            else:
                package_suffix = rel_path.replace(os.sep, '.')
                class_packages[class_name] = f"{base_package}.{package_suffix}"

    # Fix imports in each file
    fixed_count = 0
    for root, dirs, files in os.walk(output_dir):
        for filename in files:
            if not filename.endswith('.java'):
                continue

            filepath = os.path.join(root, filename)

            with open(filepath, 'r') as f:
                content = f.read()

            # Get current package
            package_match = re.search(r'package\s+([\w.]+);', content)
            if not package_match:
                continue

            current_package = package_match.group(1)

            # Get referenced classes from class_info if available
            class_name = filename[:-5]
            if class_name in class_info:
                references = set(class_info[class_name]['references'])
                if class_info[class_name]['extends']:
                    references.add(class_info[class_name]['extends'])
            else:
                continue

            # Build necessary imports
            necessary_imports = set()
            for ref_class in references:
                if ref_class in class_packages:
                    ref_package = class_packages[ref_class]
                    # Only import if from different package
                    if ref_package != current_package:
                        necessary_imports.add(f'import {ref_package}.{ref_class};')

            if not necessary_imports:
                continue

            # Remove existing imports and add new ones
            lines = content.split('\n')

            # Find package line
            package_line_idx = None
            for i, line in enumerate(lines):
                if line.strip().startswith('package '):
                    package_line_idx = i
                    break

            if package_line_idx is None:
                continue

            # Find first annotation or class declaration
            first_code_idx = None
            for i in range(package_line_idx + 1, len(lines)):
                stripped = lines[i].strip()
                if stripped and not stripped.startswith('import '):
                    first_code_idx = i
                    break

            if first_code_idx is None:
                continue

            # Rebuild file
            new_lines = []
            new_lines.extend(lines[:package_line_idx + 1])
            new_lines.append('')

            # Add necessary imports (sorted)
            for imp in sorted(necessary_imports):
                new_lines.append(imp)
            new_lines.append('')

            # Add rest of the file
            new_lines.extend(lines[first_code_idx:])

            # Write back
            with open(filepath, 'w') as f:
                f.write('\n'.join(new_lines))

            fixed_count += 1

    print(f"✅ Fixed imports in {fixed_count} files\n")


def organize_classes_by_endpoint_and_inheritance(output_dir):
    """
    Organize generated classes into folders based on endpoints and inheritance.
    - Create folders for each endpoint (e.g., POST_claims).
    - Separate into `body` and `response`.
    - Within `related`, organize by inheritance.
    """
    for class_name, fields in all_classes_fields.items():
        # Determine endpoint and type (body/response) from OpenAPI schema
        endpoint = detect_endpoint_from_class(class_name)
        class_type = detect_class_type(class_name)  # 'body' or 'response'

        # Create base folder structure
        endpoint_folder = os.path.join(output_dir, endpoint)
        type_folder = os.path.join(endpoint_folder, class_type)
        related_folder = os.path.join(type_folder, 'related')

        os.makedirs(related_folder, exist_ok=True)

        # Place the class in the appropriate folder
        class_file = f"{class_name}.java"
        class_path = os.path.join(output_dir, class_file)

        if class_name in inheritance_map:
            # Organize by inheritance
            base_class = inheritance_map[class_name]
            base_folder = os.path.join(related_folder, base_class)
            os.makedirs(base_folder, exist_ok=True)
            new_path = os.path.join(base_folder, class_file)
        else:
            # Place directly in `related`
            new_path = os.path.join(related_folder, class_file)

        if os.path.exists(class_path):
            os.rename(class_path, new_path)


def detect_endpoint_from_class(class_name):
    """Infer the endpoint name from the class name."""
    # Example logic: parse class name or use OpenAPI metadata
    return "POST_claims"  # Placeholder

def detect_class_type(class_name):
    """Determine if the class is part of the body or response."""
    # Example logic: check naming conventions or OpenAPI metadata
    return "body"  # Placeholder

# Call the organization function after generating classes
output_directory = "java"
organize_classes_by_endpoint_and_inheritance(output_directory)

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
