#!/usr/bin/env python3
"""
Generate Java classes directly from OpenAPI schema for each endpoint.
Each endpoint gets its own set of classes based solely on the OpenAPI definition.
"""
import os
import yaml
import re
import shutil

def to_java_package_name(folder_path):
    """Convert folder path to Java package name, preserving exact capitalization."""
    # Remove leading/trailing slashes
    path = folder_path.strip('/')
    # Replace path separators with dots
    path = path.replace('/', '.').replace('\\', '.')
    # Keep the exact capitalization - no conversion to lowercase
    # Just ensure valid Java package naming (alphanumeric and underscores)
    parts = path.split('.')
    valid_parts = []
    for part in parts:
        if part:
            # Keep original case
            valid_parts.append(part)
    return '.'.join(valid_parts)

def get_package_for_file(file_path, base_package, output_dir, detect_package=False):
    """
    Get the full package name for a file based on its location.
    Args:
        file_path: Full path to the Java file
        base_package: Base package name (e.g., 'com.java')
        output_dir: Root output directory (e.g., 'java')
        detect_package: If True, append folder structure to package name
    Returns:
        Full package name (e.g., 'com.java.post_claim.body.related')
    """
    if not detect_package:
        return base_package

    # Get the directory of the file
    file_dir = os.path.dirname(file_path)

    # Make paths absolute for comparison
    file_dir = os.path.abspath(file_dir)
    output_dir = os.path.abspath(output_dir)

    # Get relative path from output_dir to file_dir
    try:
        rel_path = os.path.relpath(file_dir, output_dir)
    except ValueError:
        # If paths are on different drives (Windows), use base package only
        return base_package

    # If file is directly in output_dir
    if rel_path == '.':
        return base_package

    # Convert relative path to package notation
    sub_package = to_java_package_name(rel_path)

    # Combine base package with sub-package
    if sub_package:
        return f"{base_package}.{sub_package}"
    else:
        return base_package

def to_java_class_name(name):
    """Convert schema name to Java class name."""
    if re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
        return name
    if re.match(r'^[a-z][a-zA-Z0-9]*$', name):
        return name[0].upper() + name[1:]
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    parts = re.split(r'[_\s-]+', name)
    return ''.join(word.capitalize() for word in parts if word)

def to_java_field_name(name):
    """Convert to Java field name."""
    if re.match(r'^[a-z][a-zA-Z0-9]*$', name):
        return name
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    parts = re.split(r'[_\s-]+', name)
    if not parts:
        return name
    return parts[0].lower() + ''.join(word.capitalize() for word in parts[1:] if word)

def generate_field_javadoc(description, is_required, oneof_types=None, schema=None, schemas=None):
    """Generate JavaDoc for a field including all OpenAPI and JSON Schema attributes."""
    # Merge schema attributes from allOf references if present
    merged_schema = {}
    if schema:
        merged_schema = schema.copy()

        # If schema has allOf, merge attributes from referenced schemas
        if 'allOf' in schema:
            for item in schema['allOf']:
                if isinstance(item, dict):
                    # If it's a reference, get the referenced schema
                    if '$ref' in item and schemas:
                        ref_name = item['$ref'].split('/')[-1]
                        if ref_name in schemas:
                            ref_schema = schemas[ref_name]
                            # Merge attributes (but don't override existing ones)
                            for key, value in ref_schema.items():
                                if key not in merged_schema and key != 'properties':
                                    merged_schema[key] = value
                    # Also merge inline attributes
                    for key, value in item.items():
                        if key not in merged_schema and key != '$ref':
                            merged_schema[key] = value

    # Check if we have any content to document
    has_content = description or is_required or oneof_types
    if merged_schema:
        # Check if schema has any additional attributes
        attribute_keys = [
            # Common metadata
            'title', 'description', 'default', 'example', 'examples', 'deprecated',
            # Format and nullable
            'format', 'nullable',
            # Numeric constraints
            'multipleOf', 'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum',
            # String constraints
            'minLength', 'maxLength', 'pattern',
            # Array constraints
            'minItems', 'maxItems', 'uniqueItems',
            # Object constraints
            'minProperties', 'maxProperties',
            # Enum/const
            'enum', 'const',
            # Read/Write
            'readOnly', 'writeOnly',
            # Composition
            'allOf', 'oneOf', 'anyOf', 'not',
            # Discriminator
            'discriminator',
            # External docs
            'externalDocs',
            # XML
            'xml'
        ]
        has_content = has_content or any(k in merged_schema for k in attribute_keys)

    if not has_content:
        return ""

    javadoc_lines = ["    /**"]

    # Description
    if description:
        desc = description.strip()
        if len(desc) > 80:
            words = desc.split()
            line = "     * "
            for word in words:
                if len(line) + len(word) + 1 > 100:
                    javadoc_lines.append(line)
                    line = "     * " + word
                else:
                    line += (" " if line != "     * " else "") + word
            if line != "     * ":
                javadoc_lines.append(line)
        else:
            javadoc_lines.append(f"     * {desc}")

    # OneOf types
    if oneof_types:
        types_list = ', '.join(oneof_types)
        if not description:
            javadoc_lines.append("     *")
        javadoc_lines.append(f"     * Can be one of: {types_list}")

    # Process merged schema attributes if available
    if merged_schema:
        added_blank_line = description or oneof_types

        # Title (if different from description)
        if 'title' in merged_schema and merged_schema.get('title') != description:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @title {merged_schema['title']}")

        # Deprecated
        if merged_schema.get('deprecated'):
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append("     * @deprecated This field is deprecated")

        # Read-only / Write-only
        if merged_schema.get('readOnly'):
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append("     * @readOnly This field is read-only")

        if merged_schema.get('writeOnly'):
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append("     * @writeOnly This field is write-only")

        # Nullable
        if merged_schema.get('nullable'):
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append("     * @nullable This field can be null")

        # Format (but not type - removed as requested)
        if 'format' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @format {merged_schema['format']}")

        # Numeric constraints
        if 'multipleOf' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @multipleOf {merged_schema['multipleOf']}")

        if 'minimum' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @minimum {merged_schema['minimum']}")

        if 'maximum' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @maximum {merged_schema['maximum']}")

        if 'exclusiveMinimum' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @exclusiveMinimum {merged_schema['exclusiveMinimum']}")

        if 'exclusiveMaximum' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @exclusiveMaximum {merged_schema['exclusiveMaximum']}")

        # String constraints
        if 'minLength' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @minLength {merged_schema['minLength']}")

        if 'maxLength' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @maxLength {merged_schema['maxLength']}")

        if 'pattern' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @pattern {merged_schema['pattern']}")

        # Array constraints
        if 'minItems' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @minItems {merged_schema['minItems']}")

        if 'maxItems' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @maxItems {merged_schema['maxItems']}")

        if merged_schema.get('uniqueItems'):
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append("     * @uniqueItems Items must be unique")

        # Object constraints
        if 'minProperties' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @minProperties {merged_schema['minProperties']}")

        if 'maxProperties' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @maxProperties {merged_schema['maxProperties']}")

        # Enum values
        if 'enum' in merged_schema and merged_schema['enum']:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            enum_values = ', '.join(str(v) for v in merged_schema['enum'])
            javadoc_lines.append(f"     * @enum {enum_values}")

        # Const value
        if 'const' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @const {merged_schema['const']}")

        # Default value
        if 'default' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @default {merged_schema['default']}")

        # Example value(s)
        if 'example' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            javadoc_lines.append(f"     * @example {merged_schema['example']}")

        if 'examples' in merged_schema and merged_schema['examples']:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            examples_str = ', '.join(str(v) for v in merged_schema['examples'][:3])  # Limit to 3 examples
            javadoc_lines.append(f"     * @examples {examples_str}")

        # Discriminator (for polymorphism)
        if 'discriminator' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            discriminator = merged_schema['discriminator']
            if isinstance(discriminator, dict) and 'propertyName' in discriminator:
                javadoc_lines.append(f"     * @discriminator {discriminator['propertyName']}")
            else:
                javadoc_lines.append(f"     * @discriminator {discriminator}")

        # External documentation
        if 'externalDocs' in merged_schema:
            if not added_blank_line:
                javadoc_lines.append("     *")
                added_blank_line = True
            ext_docs = merged_schema['externalDocs']
            if isinstance(ext_docs, dict):
                if 'url' in ext_docs:
                    desc = ext_docs.get('description', 'External documentation')
                    javadoc_lines.append(f"     * @see {desc}: {ext_docs['url']}")
            else:
                javadoc_lines.append(f"     * @see {ext_docs}")

    # Required (always last)
    if is_required:
        javadoc_lines.append("     * @required This field is required")

    javadoc_lines.append("     */")
    return "\n".join(javadoc_lines)

def generate_class_javadoc(description):
    """Generate JavaDoc for a class."""
    if not description:
        return ""

    javadoc_lines = ["/**"]

    # Split description into lines if too long
    desc = description.strip()
    if len(desc) > 80:
        words = desc.split()
        line = " * "
        for word in words:
            if len(line) + len(word) + 1 > 100:
                javadoc_lines.append(line)
                line = " * " + word
            else:
                line += (" " if line != " * " else "") + word
        if line != " * ":
            javadoc_lines.append(line)
    else:
        javadoc_lines.append(f" * {desc}")

    javadoc_lines.append(" */")
    return "\n".join(javadoc_lines)

def get_java_type_from_openapi(schema, schemas, visited=None, field_name=None):
    """Get Java type from OpenAPI schema definition."""
    if visited is None:
        visited = set()

    if not schema:
        return "Object"

    # Handle $ref
    if '$ref' in schema:
        ref_name = schema['$ref'].split('/')[-1]
        if ref_name in visited:
            return to_java_class_name(ref_name)
        visited.add(ref_name)
        if ref_name in schemas:
            ref_schema = schemas[ref_name]
            # If the referenced schema is just an array definition, expand it
            if ref_schema.get('type') == 'array' and 'properties' not in ref_schema and 'allOf' not in ref_schema:
                items = ref_schema.get('items', {})
                item_type = get_java_type_from_openapi(items, schemas, visited, field_name=None)
                return f"List<{item_type}>"
            return to_java_class_name(ref_name)
        return "Object"

    # Handle allOf - merge schemas
    if 'allOf' in schema:
        # Check if this is an inline inheritance case (properties + $ref)
        has_inline_props = False
        has_ref = False

        for item in schema['allOf']:
            if isinstance(item, dict):
                if 'properties' in item:
                    has_inline_props = True
                if '$ref' in item:
                    has_ref = True

        # If it has both inline properties and a ref, it's an inline class with inheritance
        # Return the class name based on field_name
        if has_inline_props and has_ref and field_name:
            return to_java_class_name(field_name)

        # If first item is $ref only, it's just inheritance reference
        if schema['allOf'] and '$ref' in schema['allOf'][0]:
            return get_java_type_from_openapi(schema['allOf'][0], schemas, visited, field_name)

        # Otherwise find any $ref
        for item in schema['allOf']:
            if '$ref' in item:
                return get_java_type_from_openapi(item, schemas, visited, field_name)
        return "Object"

    # Handle oneOf - use first type
    if 'oneOf' in schema:
        if schema['oneOf'] and '$ref' in schema['oneOf'][0]:
            return get_java_type_from_openapi(schema['oneOf'][0], schemas, visited, field_name=None)
        return "Object"

    # Handle type
    schema_type = schema.get('type', 'object')

    if schema_type == 'string':
        format_type = schema.get('format', '')
        if format_type == 'date-time':
            return "LocalDateTime"
        elif format_type == 'date':
            return "LocalDate"
        return "String"
    elif schema_type == 'integer':
        return "Long"
    elif schema_type == 'number':
        return "Double"
    elif schema_type == 'boolean':
        return "Boolean"
    elif schema_type == 'array':
        items = schema.get('items', {})
        item_type = get_java_type_from_openapi(items, schemas, visited, field_name=None)
        return f"List<{item_type}>"
    elif schema_type == 'object':
        # If it has properties, it's an inline type - generate class name from field name
        if 'properties' in schema and field_name:
            return to_java_class_name(field_name)
        return "Object"

    return "Object"

def get_all_schema_dependencies(schema_name, schemas, visited=None):
    """Recursively get all schema dependencies for a schema."""
    if visited is None:
        visited = set()

    if schema_name in visited or schema_name not in schemas:
        return visited

    schema = schemas[schema_name]

    # Skip schemas that are just array definitions (no properties, just type: array)
    # These should be used as List<ItemType>, not as separate classes
    if schema.get('type') == 'array' and 'properties' not in schema and 'allOf' not in schema:
        # Don't add this schema, but add the items type
        if 'items' in schema and '$ref' in schema['items']:
            ref_name = schema['items']['$ref'].split('/')[-1]
            get_all_schema_dependencies(ref_name, schemas, visited)
        return visited

    visited.add(schema_name)

    # Get properties
    properties = {}
    if 'properties' in schema:
        properties.update(schema['properties'])

    # Get properties from allOf
    if 'allOf' in schema:
        for item in schema['allOf']:
            if isinstance(item, dict):
                if '$ref' in item:
                    ref_name = item['$ref'].split('/')[-1]
                    get_all_schema_dependencies(ref_name, schemas, visited)
                if 'properties' in item:
                    properties.update(item['properties'])

    # Process each property
    for prop_name, prop_schema in properties.items():
        if '$ref' in prop_schema:
            ref_name = prop_schema['$ref'].split('/')[-1]
            get_all_schema_dependencies(ref_name, schemas, visited)

        if 'allOf' in prop_schema:
            for item in prop_schema['allOf']:
                if '$ref' in item:
                    ref_name = item['$ref'].split('/')[-1]
                    get_all_schema_dependencies(ref_name, schemas, visited)
                # Also check for inline properties within allOf
                if 'properties' in item:
                    for sub_prop_name, sub_prop_schema in item['properties'].items():
                        if '$ref' in sub_prop_schema:
                            ref_name = sub_prop_schema['$ref'].split('/')[-1]
                            get_all_schema_dependencies(ref_name, schemas, visited)

        if 'oneOf' in prop_schema:
            for item in prop_schema['oneOf']:
                if '$ref' in item:
                    ref_name = item['$ref'].split('/')[-1]
                    get_all_schema_dependencies(ref_name, schemas, visited)

        if prop_schema.get('type') == 'array' and 'items' in prop_schema:
            items = prop_schema['items']
            if '$ref' in items:
                ref_name = items['$ref'].split('/')[-1]
                get_all_schema_dependencies(ref_name, schemas, visited)

        # Handle inline object types with properties
        if prop_schema.get('type') == 'object' and 'properties' in prop_schema:
            # Follow references within inline object
            for inline_prop_name, inline_prop_schema in prop_schema['properties'].items():
                if '$ref' in inline_prop_schema:
                    ref_name = inline_prop_schema['$ref'].split('/')[-1]
                    get_all_schema_dependencies(ref_name, schemas, visited)
                if 'allOf' in inline_prop_schema:
                    for item in inline_prop_schema['allOf']:
                        if '$ref' in item:
                            ref_name = item['$ref'].split('/')[-1]
                            get_all_schema_dependencies(ref_name, schemas, visited)

    return visited

def get_base_class(schema_name, schemas):
    """Get base class if schema uses allOf with $ref as first element."""
    if schema_name not in schemas:
        return None

    schema = schemas[schema_name]
    if 'allOf' in schema and schema['allOf']:
        first = schema['allOf'][0]
        if '$ref' in first:
            return first['$ref'].split('/')[-1]

    return None

def get_schema_properties(schema_name, schemas, include_inherited=False):
    """Get all properties for a schema."""
    if schema_name not in schemas:
        return {}

    schema = schemas[schema_name]
    properties = {}

    # Direct properties
    if 'properties' in schema:
        properties.update(schema['properties'])

    # Properties from allOf
    if 'allOf' in schema:
        for item in schema['allOf']:
            if isinstance(item, dict):
                # Skip $ref if we don't want inherited properties
                if '$ref' in item and not include_inherited:
                    continue
                if '$ref' in item and include_inherited:
                    ref_name = item['$ref'].split('/')[-1]
                    inherited = get_schema_properties(ref_name, schemas, True)
                    properties.update(inherited)
                if 'properties' in item:
                    properties.update(item['properties'])

    return properties

def has_oneof_field(schema_name, schemas):
    """Check if schema has oneOf fields."""
    props = get_schema_properties(schema_name, schemas, False)
    for prop_name, prop_schema in props.items():
        if 'oneOf' in prop_schema:
            return prop_name, prop_schema['oneOf']
    return None, None

def find_oneof_base_class(schema_name, schemas):
    """Find if this schema is part of a oneOf and return the base class name."""
    # Search through all schemas to find oneOf references
    for parent_schema_name, parent_schema in schemas.items():
        props = get_schema_properties(parent_schema_name, schemas, False)
        for prop_name, prop_schema in props.items():
            if 'oneOf' in prop_schema:
                # Check if our schema is in this oneOf
                for option in prop_schema['oneOf']:
                    if '$ref' in option:
                        ref_name = option['$ref'].split('/')[-1]
                        if ref_name == schema_name:
                            # This schema is part of a oneOf, return the base class name
                            return to_java_class_name(prop_name)
    return None

def generate_java_class_from_schema(schema_name, schemas, package, processed=None, enable_javadoc=True, enable_imports=False):
    """Generate Java class from OpenAPI schema."""
    if processed is None:
        processed = set()

    if schema_name in processed or schema_name not in schemas:
        return None

    schema = schemas[schema_name]

    # Skip schemas that are just array definitions (no properties, just type: array)
    # These should be used as List<ItemType>, not as separate classes
    if schema.get('type') == 'array' and 'properties' not in schema and 'allOf' not in schema:
        return None

    processed.add(schema_name)

    class_name = to_java_class_name(schema_name)

    # Check for base class from allOf
    base_class = get_base_class(schema_name, schemas)
    base_class_name = to_java_class_name(base_class) if base_class else None

    # If no allOf base class, check if this is part of a oneOf
    if not base_class_name:
        oneof_base = find_oneof_base_class(schema_name, schemas)
        if oneof_base:
            base_class_name = oneof_base

    # Get properties (exclude inherited if has base class)
    all_props = get_schema_properties(schema_name, schemas, True)
    if base_class_name:
        base_props = get_schema_properties(base_class, schemas, True)
        own_props = {k: v for k, v in all_props.items() if k not in base_props}
    else:
        own_props = all_props

    # Check for oneOf fields
    oneof_field_name, oneof_types = has_oneof_field(schema_name, schemas)
    generic_param = None
    if oneof_field_name and oneof_types:
        # Create generic parameter
        base_type_name = to_java_class_name(oneof_field_name)
        generic_param = f"T{base_type_name} extends {base_type_name}"

    # Build imports
    imports = set()
    imports.add("import lombok.Data;")
    imports.add("import lombok.NoArgsConstructor;")
    imports.add("import lombok.AllArgsConstructor;")

    if base_class_name:
        imports.add("import lombok.EqualsAndHashCode;")
    else:
        imports.add("import lombok.Builder;")

    # Build fields
    fields = []
    referenced_classes = set()

    # Get required fields list from schema
    required_fields = schema.get('required', [])
    # Also check in allOf items
    if 'allOf' in schema:
        for item in schema['allOf']:
            if isinstance(item, dict) and 'required' in item:
                required_fields.extend(item['required'])

    for prop_name, prop_schema in own_props.items():
        java_field = to_java_field_name(prop_name)

        # Check if this field is required
        is_required = prop_name in required_fields

        # Get field description
        field_description = prop_schema.get('description', '')

        # Check if this is the oneOf field
        if oneof_field_name and prop_name == oneof_field_name:
            java_type = f"T{to_java_class_name(prop_name)}"
            types_list = [to_java_class_name(t.get('$ref', '').split('/')[-1]) for t in oneof_types if '$ref' in t]

            # Generate JavaDoc for oneOf field if enabled
            if enable_javadoc:
                javadoc = generate_field_javadoc(field_description, is_required, types_list, prop_schema, schemas)
                if javadoc:
                    fields.append(javadoc)

            # Add base class to referenced classes
            referenced_classes.add(to_java_class_name(prop_name))
        else:
            java_type = get_java_type_from_openapi(prop_schema, schemas, field_name=prop_name)

            # Extract class names from type
            # Handle List<ClassName>, ClassName, etc.
            type_classes = re.findall(r'\b([A-Z][a-zA-Z0-9]*)\b', java_type)
            for type_class in type_classes:
                if type_class not in ['String', 'Integer', 'Long', 'Double', 'Boolean', 'LocalDate', 'LocalDateTime', 'Object', 'List']:
                    referenced_classes.add(type_class)

            # Generate JavaDoc for regular field if enabled
            if enable_javadoc:
                javadoc = generate_field_javadoc(field_description, is_required, None, prop_schema, schemas)
                if javadoc:
                    fields.append(javadoc)

        # Add necessary imports
        if "List" in java_type:
            imports.add("import java.util.List;")
        if "LocalDateTime" in java_type:
            imports.add("import java.time.LocalDateTime;")
        if "LocalDate" in java_type:
            imports.add("import java.time.LocalDate;")

        # Add field declaration
        fields.append(f"    private {java_type} {java_field};")

    # Add base class to referenced classes if exists
    if base_class_name:
        referenced_classes.add(base_class_name)

    # Add imports for referenced classes if enabled
    if enable_imports:
        for ref_class in sorted(referenced_classes):
            imports.add(f"import {package}.{ref_class};")

    # Build class
    java_code = f"package {package};\n\n"
    java_code += "\n".join(sorted(imports)) + "\n\n"

    # Add class JavaDoc if enabled
    if enable_javadoc:
        class_description = schema.get('description', '')
        if not class_description:
            class_description = f"{class_name} class."
        class_javadoc = generate_class_javadoc(class_description)
        if class_javadoc:
            java_code += class_javadoc + "\n"

    java_code += "@Data\n"

    if base_class_name:
        java_code += "@EqualsAndHashCode(callSuper = true)\n"

    java_code += "@NoArgsConstructor\n"
    java_code += "@AllArgsConstructor\n"

    # Class declaration
    if base_class_name:
        if generic_param:
            java_code += f"public class {class_name}<{generic_param}> extends {base_class_name} {{\n\n"
        else:
            java_code += f"public class {class_name} extends {base_class_name} {{\n\n"
    else:
        java_code += "@Builder\n"
        if generic_param:
            java_code += f"public class {class_name}<{generic_param}> {{\n\n"
        else:
            java_code += f"public class {class_name} {{\n\n"

    if fields:
        java_code += "\n".join(fields)
    else:
        if base_class_name:
            java_code += f"    // All fields inherited from {base_class_name}"
        else:
            java_code += "    // No fields"

    java_code += "\n}\n"

    return java_code

def generate_base_class_for_oneof(base_name, package, enable_javadoc=True):
    """Generate abstract base class for oneOf."""
    java_code = f"package {package};\n\n"
    java_code += "import lombok.Data;\n"
    java_code += "import lombok.NoArgsConstructor;\n"
    java_code += "import lombok.AllArgsConstructor;\n\n"

    if enable_javadoc:
        java_code += "/**\n"
        java_code += " * Polymorphic base class for oneOf types.\n"
        java_code += " * All concrete implementations will extend this class.\n"
        java_code += " */\n"

    java_code += "@Data\n"
    java_code += "@NoArgsConstructor\n"
    java_code += "@AllArgsConstructor\n"
    java_code += f"public abstract class {base_name} {{\n"
    java_code += "}\n"
    return java_code

def organize_classes_in_folder(folder_dir, main_class_name, all_generated_classes, schemas):
    """
    Organize classes in a folder: main class at root, related in subfolder grouped by inheritance.
    """
    import shutil

    # Create a temporary directory to hold files during reorganization
    temp_dir = folder_dir + "_temp"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    # Move all files to temp
    for filename in os.listdir(folder_dir):
        if filename.endswith('.java'):
            shutil.move(
                os.path.join(folder_dir, filename),
                os.path.join(temp_dir, filename)
            )

    # Move main class back to root
    main_file = f"{main_class_name}.java"
    if os.path.exists(os.path.join(temp_dir, main_file)):
        shutil.move(
            os.path.join(temp_dir, main_file),
            os.path.join(folder_dir, main_file)
        )

    # Create related folder
    related_dir = os.path.join(folder_dir, 'related')
    os.makedirs(related_dir, exist_ok=True)

    # Analyze inheritance relationships
    class_info = {}
    for filename in os.listdir(temp_dir):
        if not filename.endswith('.java'):
            continue

        class_name = filename[:-5]
        filepath = os.path.join(temp_dir, filename)

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract extends
        extends_match = re.search(r'extends\s+(\w+)', content)
        extends = extends_match.group(1) if extends_match else None

        class_info[class_name] = {
            'filename': filename,
            'extends': extends,
            'children': [],
            'content': content
        }

    # Build children relationships
    for class_name, info in class_info.items():
        if info['extends'] and info['extends'] in class_info:
            class_info[info['extends']]['children'].append(class_name)

    def to_camel_case(name):
        """Convert PascalCase to camelCase."""
        if not name:
            return name
        return name[0].lower() + name[1:]

    # Organize files: group by inheritance
    processed = set()

    # First, handle inheritance groups (base class + children)
    for class_name, info in class_info.items():
        if class_name in processed:
            continue

        # If this class has children, create a subfolder for the family
        if info['children']:
            family_dir = os.path.join(related_dir, to_camel_case(class_name))
            os.makedirs(family_dir, exist_ok=True)

            # Move base class
            dest = os.path.join(family_dir, info['filename'])
            with open(dest, 'w', encoding='utf-8') as f:
                f.write(info['content'])
            processed.add(class_name)

            # Move children
            for child_name in info['children']:
                child_info = class_info[child_name]
                dest = os.path.join(family_dir, child_info['filename'])
                with open(dest, 'w', encoding='utf-8') as f:
                    f.write(child_info['content'])
                processed.add(child_name)

    # Move remaining classes (no inheritance) to related root
    for class_name, info in class_info.items():
        if class_name in processed:
            continue

        dest = os.path.join(related_dir, info['filename'])
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(info['content'])
        processed.add(class_name)

    # Clean up temp directory
    shutil.rmtree(temp_dir)

def generate_inline_classes(schema_name, schemas, package, folder_dir):
    """
    Generate Java classes for inline object types found in a schema.
    Returns a set of generated class names.
    """
    if schema_name not in schemas:
        return set()

    generated = set()
    schema = schemas[schema_name]

    # Get all properties
    properties = {}
    if 'properties' in schema:
        properties.update(schema['properties'])

    if 'allOf' in schema:
        for item in schema['allOf']:
            if isinstance(item, dict) and 'properties' in item:
                properties.update(item['properties'])

    # Check each property for inline object types
    for prop_name, prop_schema in properties.items():
        # Case 1: Direct inline object with properties
        if prop_schema.get('type') == 'object' and 'properties' in prop_schema:
            # This is an inline type - generate a class for it
            inline_class_name = to_java_class_name(prop_name)

            # Create inline schema as a standalone schema
            inline_schema = {
                'type': 'object',
                'properties': prop_schema.get('properties', {}),
                'required': prop_schema.get('required', [])
            }

            # Generate the class
            java_code = generate_java_class_from_inline_schema(
                inline_class_name,
                inline_schema,
                schemas,
                package
            )

            if java_code:
                filepath = os.path.join(folder_dir, f"{inline_class_name}.java")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(java_code)
                generated.add(inline_class_name)

        # Case 2: allOf with inline properties + $ref (inheritance with extra properties)
        elif 'allOf' in prop_schema:
            # Check if this allOf has inline properties (not just refs)
            has_inline_props = False
            base_class_ref = None
            inline_props = {}

            for item in prop_schema['allOf']:
                if isinstance(item, dict):
                    if 'properties' in item:
                        has_inline_props = True
                        inline_props.update(item.get('properties', {}))
                    if '$ref' in item:
                        base_class_ref = item['$ref'].split('/')[-1]

            # If it has both inline properties and a base class, generate an inline class with inheritance
            if has_inline_props and base_class_ref:
                inline_class_name = to_java_class_name(prop_name)

                # Create inline schema with inheritance
                inline_schema = {
                    'type': 'object',
                    'properties': inline_props,
                    'base_class': base_class_ref  # Custom property for base class
                }

                # Generate the class
                java_code = generate_java_class_from_inline_schema(
                    inline_class_name,
                    inline_schema,
                    schemas,
                    package
                )

                if java_code:
                    filepath = os.path.join(folder_dir, f"{inline_class_name}.java")
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(java_code)
                    generated.add(inline_class_name)

    return generated

def generate_java_class_from_inline_schema(class_name, inline_schema, schemas, package, enable_javadoc=True, enable_imports=False):
    """Generate Java class from an inline schema definition."""
    imports = set()
    imports.add("import lombok.Data;")
    imports.add("import lombok.NoArgsConstructor;")
    imports.add("import lombok.AllArgsConstructor;")

    # Check if this inline class has a base class
    base_class = inline_schema.get('base_class')
    if base_class:
        imports.add("import lombok.EqualsAndHashCode;")
    else:
        imports.add("import lombok.Builder;")

    fields = []
    referenced_classes = set()

    # Add base class to referenced classes
    if base_class:
        referenced_classes.add(base_class)

    properties = inline_schema.get('properties', {})

    # Get required fields list from inline schema
    required_fields = inline_schema.get('required', [])

    for prop_name, prop_schema in properties.items():
        java_field = to_java_field_name(prop_name)
        java_type = get_java_type_from_openapi(prop_schema, schemas, field_name=prop_name)

        # Check if this field is required
        is_required = prop_name in required_fields

        # Get field description
        field_description = prop_schema.get('description', '')

        # Extract class names from type
        type_classes = re.findall(r'\b([A-Z][a-zA-Z0-9]*)\b', java_type)
        for type_class in type_classes:
            if type_class not in ['String', 'Integer', 'Long', 'Double', 'Boolean', 'LocalDate', 'LocalDateTime', 'Object', 'List']:
                referenced_classes.add(type_class)

        # Add necessary imports
        if "List" in java_type:
            imports.add("import java.util.List;")
        if "LocalDateTime" in java_type:
            imports.add("import java.time.LocalDateTime;")
        if "LocalDate" in java_type:
            imports.add("import java.time.LocalDate;")

        # Generate JavaDoc for field if enabled
        if enable_javadoc:
            javadoc = generate_field_javadoc(field_description, is_required, None, prop_schema, schemas)
            if javadoc:
                fields.append(javadoc)

        # Add field declaration
        fields.append(f"    private {java_type} {java_field};")

    # Add imports for referenced classes if enabled
    if enable_imports:
        for ref_class in sorted(referenced_classes):
            imports.add(f"import {package}.{ref_class};")

    # Build class
    java_code = f"package {package};\n\n"
    java_code += "\n".join(sorted(imports)) + "\n\n"

    # Add class JavaDoc if enabled
    if enable_javadoc:
        class_description = inline_schema.get('description', '')
        if not class_description:
            class_description = f"{class_name} class."
        class_javadoc = generate_class_javadoc(class_description)
        if class_javadoc:
            java_code += class_javadoc + "\n"

    java_code += "@Data\n"

    if base_class:
        java_code += "@EqualsAndHashCode(callSuper = true)\n"

    java_code += "@NoArgsConstructor\n"
    java_code += "@AllArgsConstructor\n"

    if not base_class:
        java_code += "@Builder\n"

    if base_class:
        java_code += f"public class {class_name} extends {base_class} {{\n\n"
    else:
        java_code += f"public class {class_name} {{\n\n"

    if fields:
        java_code += "\n".join(fields)
    else:
        if base_class:
            java_code += f"    // All fields inherited from {base_class}"
        else:
            java_code += "    // No fields"

    java_code += "\n}\n"

    return java_code

def process_endpoint(endpoint_name, request_schema, response_schemas, schemas, output_dir, package, enable_javadoc=True, enable_imports=False, detect_package=False, base_output_dir=None):
    """Process a single endpoint and generate all necessary classes.

    Returns:
        dict: Mapping of class names to their file paths for this endpoint only.
    """
    print(f"\n📁 Processing endpoint: {endpoint_name}")

    if base_output_dir is None:
        base_output_dir = output_dir

    endpoint_dir = os.path.join(output_dir, endpoint_name)
    all_schemas_for_endpoint = set()
    endpoint_classes = {}  # Track all classes generated for this endpoint

    # Process request body
    if request_schema and request_schema in schemas:
        print(f"   📄 Request: {request_schema}")
        body_dir = os.path.join(endpoint_dir, 'body')
        os.makedirs(body_dir, exist_ok=True)

        # Get all dependencies for request
        deps = get_all_schema_dependencies(request_schema, schemas)
        all_schemas_for_endpoint.update(deps)

        # Generate classes
        generated = set()
        for schema_name in sorted(deps):
            if schema_name in generated:
                continue

            # Check for oneOf base class
            oneof_field, oneof_types = has_oneof_field(schema_name, schemas)
            if oneof_field and oneof_types:
                base_name = to_java_class_name(oneof_field)
                if base_name not in generated:
                    java_code = generate_base_class_for_oneof(base_name, package, enable_javadoc)
                    filepath = os.path.join(body_dir, f"{base_name}.java")
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(java_code)
                    generated.add(base_name)
                    endpoint_classes[base_name] = filepath

            java_code = generate_java_class_from_schema(schema_name, schemas, package, enable_javadoc=enable_javadoc, enable_imports=enable_imports)
            if java_code:
                filepath = os.path.join(body_dir, f"{to_java_class_name(schema_name)}.java")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(java_code)
                generated.add(schema_name)
                endpoint_classes[to_java_class_name(schema_name)] = filepath

        # Generate inline classes
        for schema_name in sorted(deps):
            inline_generated = generate_inline_classes(schema_name, schemas, package, body_dir)
            generated.update(inline_generated)
            # Track inline classes
            for inline_class in inline_generated:
                inline_filepath = os.path.join(body_dir, f"{to_java_class_name(inline_class)}.java")
                if os.path.exists(inline_filepath):
                    endpoint_classes[to_java_class_name(inline_class)] = inline_filepath

        print(f"      ✅ Generated {len(generated)} classes for request")

        # Organize classes in body folder
        organize_classes_in_folder(body_dir, to_java_class_name(request_schema), generated, schemas)
        print(f"      📂 Organized into main class + related/")

        # Update endpoint_classes with new paths after reorganization
        for class_name in list(endpoint_classes.keys()):
            # Find the new location of this class
            for root, dirs, files in os.walk(body_dir):
                if f"{class_name}.java" in files:
                    endpoint_classes[class_name] = os.path.join(root, f"{class_name}.java")
                    break

    # Process responses
    for response_schema in response_schemas:
        if response_schema not in schemas:
            continue

        print(f"   📄 Response: {response_schema}")
        response_dir = os.path.join(endpoint_dir, 'response')
        os.makedirs(response_dir, exist_ok=True)

        # Get all dependencies for response
        deps = get_all_schema_dependencies(response_schema, schemas)
        all_schemas_for_endpoint.update(deps)

        # Generate classes
        generated = set()
        for schema_name in sorted(deps):
            if schema_name in generated:
                continue

            # Check for oneOf base class
            oneof_field, oneof_types = has_oneof_field(schema_name, schemas)
            if oneof_field and oneof_types:
                base_name = to_java_class_name(oneof_field)
                if base_name not in generated:
                    java_code = generate_base_class_for_oneof(base_name, package, enable_javadoc)
                    filepath = os.path.join(response_dir, f"{base_name}.java")
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(java_code)
                    generated.add(base_name)
                    endpoint_classes[base_name] = filepath

            java_code = generate_java_class_from_schema(schema_name, schemas, package, enable_javadoc=enable_javadoc, enable_imports=enable_imports)
            if java_code:
                filepath = os.path.join(response_dir, f"{to_java_class_name(schema_name)}.java")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(java_code)
                generated.add(schema_name)
                endpoint_classes[to_java_class_name(schema_name)] = filepath

        # Generate inline classes
        for schema_name in sorted(deps):
            inline_generated = generate_inline_classes(schema_name, schemas, package, response_dir)
            generated.update(inline_generated)
            # Track inline classes
            for inline_class in inline_generated:
                inline_filepath = os.path.join(response_dir, f"{to_java_class_name(inline_class)}.java")
                if os.path.exists(inline_filepath):
                    endpoint_classes[to_java_class_name(inline_class)] = inline_filepath

        print(f"      ✅ Generated {len(generated)} classes for response")

        # Organize classes in response folder
        organize_classes_in_folder(response_dir, to_java_class_name(response_schema), generated, schemas)
        print(f"      📂 Organized into main class + related/")

        # Update endpoint_classes with new paths after reorganization
        for class_name in list(endpoint_classes.keys()):
            # Find the new location of this class
            for root, dirs, files in os.walk(response_dir):
                if f"{class_name}.java" in files:
                    endpoint_classes[class_name] = os.path.join(root, f"{class_name}.java")
                    break

    return endpoint_classes

def generate_unused_schemas(schemas, output_dir, package, enable_javadoc=True, enable_imports=False):
    """
    Generate classes for schemas that are not used in any endpoint.
    These are placed in a NO_ENDPOINT folder organized by inheritance.
    """
    # First, find all schemas already generated (used in endpoints)
    used_schemas = set()
    for root, dirs, files in os.walk(output_dir):
        # Skip NO_ENDPOINT folder if it exists
        if 'NO_ENDPOINT' in root:
            continue
        for filename in files:
            if filename.endswith('.java'):
                class_name = filename[:-5]  # Remove .java
                used_schemas.add(class_name)

    # Find schemas that should be generated but are not used
    unused_schemas = []
    for schema_name, schema in schemas.items():
        # Skip array-only schemas
        if schema.get('type') == 'array' and 'properties' not in schema and 'allOf' not in schema:
            continue

        class_name = to_java_class_name(schema_name)
        if class_name not in used_schemas:
            unused_schemas.append(schema_name)

    if not unused_schemas:
        print("   No unused schemas found")
        return

    print(f"   Found {len(unused_schemas)} unused schemas")

    # Create NO_ENDPOINT folder
    no_endpoint_dir = os.path.join(output_dir, 'NO_ENDPOINT')
    os.makedirs(no_endpoint_dir, exist_ok=True)

    # Generate classes for unused schemas
    generated = set()
    for schema_name in sorted(unused_schemas):
        # Check for oneOf base class
        oneof_field, oneof_types = has_oneof_field(schema_name, schemas)
        if oneof_field and oneof_types:
            base_name = to_java_class_name(oneof_field)
            if base_name not in generated:
                java_code = generate_base_class_for_oneof(base_name, package, enable_javadoc)
                filepath = os.path.join(no_endpoint_dir, f"{base_name}.java")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(java_code)
                generated.add(base_name)

        java_code = generate_java_class_from_schema(schema_name, schemas, package, enable_javadoc=enable_javadoc, enable_imports=enable_imports)
        if java_code:
            filepath = os.path.join(no_endpoint_dir, f"{to_java_class_name(schema_name)}.java")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(java_code)
            generated.add(schema_name)

        # Generate inline classes for this schema
        inline_generated = generate_inline_classes(schema_name, schemas, package, no_endpoint_dir)
        generated.update(inline_generated)

    print(f"   ✅ Generated {len(generated)} classes in NO_ENDPOINT/")

    # Organize by inheritance
    organize_no_endpoint_by_inheritance(no_endpoint_dir, schemas)
    print(f"   📂 Organized by inheritance")

def organize_no_endpoint_by_inheritance(no_endpoint_dir, schemas):
    """
    Organize NO_ENDPOINT folder by inheritance relationships.
    """
    import shutil

    # Analyze all files in NO_ENDPOINT
    class_info = {}
    for filename in os.listdir(no_endpoint_dir):
        if not filename.endswith('.java'):
            continue

        class_name = filename[:-5]
        filepath = os.path.join(no_endpoint_dir, filename)

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract extends
        extends_match = re.search(r'extends\s+(\w+)', content)
        extends = extends_match.group(1) if extends_match else None

        class_info[class_name] = {
            'filename': filename,
            'extends': extends,
            'children': [],
            'content': content
        }

    # Build children relationships
    for class_name, info in class_info.items():
        if info['extends'] and info['extends'] in class_info:
            class_info[info['extends']]['children'].append(class_name)

    def to_camel_case(name):
        """Convert PascalCase to camelCase."""
        if not name:
            return name
        return name[0].lower() + name[1:]

    # Organize files: group by inheritance
    processed = set()

    # First, handle inheritance groups (base class + children)
    for class_name, info in class_info.items():
        if class_name in processed:
            continue

        # If this class has children, create a subfolder for the family
        if info['children']:
            family_dir = os.path.join(no_endpoint_dir, to_camel_case(class_name))
            os.makedirs(family_dir, exist_ok=True)

            # Move base class
            src = os.path.join(no_endpoint_dir, info['filename'])
            dest = os.path.join(family_dir, info['filename'])
            if os.path.exists(src):
                shutil.move(src, dest)
            processed.add(class_name)

            # Move children
            for child_name in info['children']:
                child_info = class_info[child_name]
                src = os.path.join(no_endpoint_dir, child_info['filename'])
                dest = os.path.join(family_dir, child_info['filename'])
                if os.path.exists(src):
                    shutil.move(src, dest)
                processed.add(child_name)

def update_file_packages(output_dir, base_package, enable_imports, detect_package):
    """
    Update package declarations and imports in all Java files if detect_package is enabled.
    Only updates if enable_imports is True.
    """
    if not enable_imports or not detect_package:
        return

    print(f"\n🔄 Updating packages based on folder structure...")

    # First pass: collect all class locations
    class_to_package = {}
    for root, dirs, files in os.walk(output_dir):
        for filename in files:
            if not filename.endswith('.java'):
                continue

            filepath = os.path.join(root, filename)
            class_name = filename[:-5]
            pkg = get_package_for_file(filepath, base_package, output_dir, detect_package)
            class_to_package[class_name] = pkg

    # Second pass: update package declarations and imports
    updated_count = 0
    for root, dirs, files in os.walk(output_dir):
        for filename in files:
            if not filename.endswith('.java'):
                continue

            filepath = os.path.join(root, filename)

            # Read file content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Calculate correct package for this file
            correct_package = get_package_for_file(filepath, base_package, output_dir, detect_package)

            # Replace package declaration
            content = re.sub(r'^package\s+[\w.]+;', f'package {correct_package};', content, flags=re.MULTILINE)

            # Update imports: replace base_package.ClassName with correct_package.ClassName
            # Find all import statements
            import_pattern = r'import\s+([\w.]+)\.([\w]+);'

            def replace_import(match):
                full_package = match.group(1)
                class_name = match.group(2)

                # If this is one of our generated classes, update its package
                if class_name in class_to_package:
                    return f'import {class_to_package[class_name]}.{class_name};'
                else:
                    # Keep original import (for java.util, lombok, etc.)
                    return match.group(0)

            content = re.sub(import_pattern, replace_import, content)

            # Write back
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            updated_count += 1

    print(f"   ✅ Updated {updated_count} files with dynamic packages")

def update_endpoint_packages(endpoint_dir, endpoint_classes, base_package, output_dir, detect_package):
    """
    Update package declarations for a specific endpoint using only its own classes.

    Args:
        endpoint_dir: Directory of the endpoint
        endpoint_classes: Dict mapping class names to file paths for this endpoint
        base_package: Base package name
        output_dir: Root output directory
        detect_package: Whether to detect package from folder structure
    """
    if not detect_package:
        return

    # Build class to package mapping for this endpoint only
    class_to_package = {}
    for class_name, filepath in endpoint_classes.items():
        pkg = get_package_for_file(filepath, base_package, output_dir, detect_package)
        class_to_package[class_name] = pkg

    # Update all files in this endpoint directory
    updated_count = 0
    for root, dirs, files in os.walk(endpoint_dir):
        for filename in files:
            if not filename.endswith('.java'):
                continue

            filepath = os.path.join(root, filename)

            # Read file content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Calculate correct package for this file
            correct_package = get_package_for_file(filepath, base_package, output_dir, detect_package)

            # Replace package declaration
            content = re.sub(r'^package\s+[\w.]+;', f'package {correct_package};', content, flags=re.MULTILINE)

            # Update imports: replace base_package.ClassName with correct_package.ClassName
            # Find all import statements
            import_pattern = r'import\s+([\w.]+)\.([\w]+);'

            def replace_import(match):
                full_package = match.group(1)
                class_name = match.group(2)

                # If this is one of our generated classes in this endpoint, update its package
                if class_name in class_to_package:
                    return f'import {class_to_package[class_name]}.{class_name};'
                else:
                    # Keep original import (for java.util, lombok, etc.)
                    return match.group(0)

            content = re.sub(import_pattern, replace_import, content)

            # Remove imports of classes that are in the same package as the current file
            # Split content into lines to process imports
            lines = content.split('\n')
            filtered_lines = []

            # Find where imports end (after package and imports, before class declaration)
            import_section_end = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith('package') and not line.strip().startswith('import') and not line.strip().startswith('//') and not line.strip().startswith('/*') and not line.strip().startswith('*'):
                    import_section_end = i
                    break

            # Get the code section (everything after imports)
            code_section = '\n'.join(lines[import_section_end:])

            for i, line in enumerate(lines):
                # Check if this is an import statement
                import_match = re.match(r'import\s+([\w.]+)\.([\w]+);', line)
                if import_match:
                    import_package = import_match.group(1)
                    imported_class = import_match.group(2)

                    # Only keep the import if it's from a different package
                    if import_package != correct_package:
                        # Also check if the import is actually used in the code section
                        # Look for the class name with strict word boundaries
                        # Use negative lookahead/lookbehind to avoid partial matches
                        # For example, LocalDate should not match LocalDateTime
                        class_pattern = r'(?<![a-zA-Z0-9])' + re.escape(imported_class) + r'(?![a-zA-Z0-9])'
                        # Search only in the code section (not in imports)
                        if re.search(class_pattern, code_section):
                            filtered_lines.append(line)
                        # else: skip unused import
                    # else: skip import from same package
                else:
                    filtered_lines.append(line)

            content = '\n'.join(filtered_lines)

            # Write back
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            updated_count += 1

    if updated_count > 0:
        print(f"      🔄 Updated {updated_count} files with endpoint-specific packages and imports")


def main():
    from config import OPENAPI_FILE, JAVA_FOLDER, BASE_PACKAGE, ENABLE_JAVADOC, ENABLE_IMPORTS, DETECT_PACKAGE

    openapi_file = OPENAPI_FILE
    output_dir = JAVA_FOLDER
    package = BASE_PACKAGE
    enable_javadoc = ENABLE_JAVADOC
    enable_imports = ENABLE_IMPORTS
    detect_package = DETECT_PACKAGE

    print("=== Generating Java classes from OpenAPI schema ===\n")
    print(f"Configuration:")
    print(f"  - Package: {package}")
    print(f"  - Output: {output_dir}")
    print(f"  - JavaDoc: {'enabled' if enable_javadoc else 'disabled'}")
    print(f"  - Imports: {'enabled' if enable_imports else 'disabled'}")
    print(f"  - Detect Package: {'enabled' if detect_package else 'disabled'}\n")

    # Load OpenAPI
    with open(openapi_file, 'r', encoding='utf-8') as f:
        openapi_spec = yaml.safe_load(f)

    schemas = openapi_spec.get('components', {}).get('schemas', {})
    print(f"Loaded {len(schemas)} schemas from OpenAPI\n")

    # Clear output directory
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    # Extract endpoints
    paths = openapi_spec.get('paths', {})
    responses_comp = openapi_spec.get('components', {}).get('responses', {})

    endpoint_count = 0
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method not in ['get', 'post', 'put', 'patch', 'delete']:
                continue

            # Generate endpoint name
            endpoint_parts = [p for p in path.split('/') if p and not p.startswith('{')]
            endpoint_name = f"{method.upper()}_{'_'.join(endpoint_parts)}" if endpoint_parts else f"{method.upper()}_root"

            # Extract request schema
            request_schema = None
            request_body = operation.get('requestBody', {})
            if request_body:
                content = request_body.get('content', {})
                json_content = content.get('application/json', {})
                schema = json_content.get('schema', {})
                if '$ref' in schema:
                    request_schema = schema['$ref'].split('/')[-1]

            # Extract response schemas
            response_schemas = []
            responses = operation.get('responses', {})
            for status_code, response in responses.items():
                if status_code.startswith('2'):
                    if '$ref' in response:
                        ref_name = response['$ref'].split('/')[-1]
                        if ref_name in responses_comp:
                            resp_content = responses_comp[ref_name].get('content', {})
                            json_content = resp_content.get('application/json', {})
                            schema = json_content.get('schema', {})
                            if '$ref' in schema:
                                response_schemas.append(schema['$ref'].split('/')[-1])
                    else:
                        resp_content = response.get('content', {})
                        json_content = resp_content.get('application/json', {})
                        schema = json_content.get('schema', {})
                        if '$ref' in schema:
                            response_schemas.append(schema['$ref'].split('/')[-1])

            # Process endpoint
            if request_schema or response_schemas:
                endpoint_classes = process_endpoint(endpoint_name, request_schema, response_schemas, schemas, output_dir, package, enable_javadoc, enable_imports, detect_package, output_dir)
                # Update packages for this endpoint using only its classes
                endpoint_dir = os.path.join(output_dir, endpoint_name)
                update_endpoint_packages(endpoint_dir, endpoint_classes, package, output_dir, detect_package)
                endpoint_count += 1

    print(f"\n✅ Processed {endpoint_count} endpoints")
    print(f"   Generated classes in: {output_dir}/")

    # Generate unused schemas in NO_ENDPOINT folder
    print(f"\n📦 Processing unused schemas...")
    generate_unused_schemas(schemas, output_dir, package, enable_javadoc, enable_imports)


if __name__ == '__main__':
    main()
