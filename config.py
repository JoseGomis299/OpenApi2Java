#!/usr/bin/env python3
"""
Configuration management for OpenAPI to Java generator.
Loads configuration from config.yaml or creates default if not exists.
"""
import os
import yaml

# Default configuration
DEFAULT_CONFIG = {
    'json': {
        'examples_folder': 'examples'
    },
    'java': {
        'base_package': 'com.java',
        'java_folder': 'java',
        'enable_javadoc': True,
        'enable_imports': False,
        'detect_package': True
    },
    'feign': {
        'base_package': 'com.java.client',
        'feign_folder': 'feign',
        'enable_javadoc': True,
        'interface_suffix': 'Client',
        'generate_config': True,
        'grouping_strategy': 'single-client',
        'use_response_entity': False,
        'format_one_param_per_line': True,
        'add_feign_annotation': True,
        'ignore_optional_params': False,
        'ignore_params_list': []
    },
    'openapi_definitions_dir': 'openApiDefinitions'
}

CONFIG_FILE = 'config.yaml'

def load_config():
    """Load configuration from config.yaml or create default."""
    if not os.path.exists(CONFIG_FILE):
        print(f"⚙️  Creating default configuration file: {CONFIG_FILE}")
        create_default_config()

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config is None:
                config = DEFAULT_CONFIG.copy()

            # Merge with defaults to ensure all keys exist (deep merge for nested dicts)
            def deep_merge(default, loaded):
                """Deep merge loaded config with defaults."""
                result = default.copy()
                for key, value in loaded.items():
                    if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = deep_merge(result[key], value)
                    else:
                        result[key] = value
                return result

            config = deep_merge(DEFAULT_CONFIG, config)
            return config
    except Exception as e:
        print(f"⚠️  Error loading {CONFIG_FILE}: {e}")
        print("Using default configuration...")
        return DEFAULT_CONFIG.copy()

def create_default_config():
    """Create default config.yaml file."""
    config_content = """# OpenAPI to Java Generator Configuration

json:
  examples_folder: examples

java:
  base_package: com.java
  java_folder: java
  enable_javadoc: true
  enable_imports: true
  detect_package: true

openapi_definitions_dir: openApiDefinitions

feign:
  base_package: com.java.client
  feign_folder: feign
  enable_javadoc: true
  interface_suffix: Client
  generate_config: true
  grouping_strategy: single-client
  use_response_entity: false
  format_one_param_per_line: true
  add_feign_annotation: true
  ignore_optional_params: false
  ignore_params_list: []
"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print(f"✅ Created {CONFIG_FILE} with default values")
    except Exception as e:
        print(f"❌ Error creating {CONFIG_FILE}: {e}")

def get_config():
    """Get configuration dictionary."""
    return load_config()

def ensure_openapi_definitions_dir():
    """Ensure openapi_definitions_dir exists, create with example if it doesn't."""
    config = load_config()
    openapi_dir = config.get('openapi_definitions_dir', 'openApiDefinitions')

    if not os.path.exists(openapi_dir):
        print(f"📁 Creating OpenAPI definitions directory: {openapi_dir}")
        os.makedirs(openapi_dir, exist_ok=True)

        # Create example file
        example_file = os.path.join(openapi_dir, 'example-api.yaml')
        example_content = """openapi: 3.0.1
info:
  title: Example API
  description: Example OpenAPI specification
  version: "1.0"
paths:
  /example:
    get:
      tags:
        - Example
      summary: Example endpoint
      operationId: getExample
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ExampleResponse'
components:
  schemas:
    ExampleResponse:
      type: object
      properties:
        message:
          type: string
"""
        with open(example_file, 'w', encoding='utf-8') as f:
            f.write(example_content)

        print(f"   ✅ Created example file: {example_file}")
        print(f"   ℹ️  Add your OpenAPI YAML files to {openapi_dir} directory")

    return openapi_dir

def get_openapi_definition_files():
    """Get list of OpenAPI definition files to process from openapi_definitions_dir."""
    config = load_config()
    openapi_dir = ensure_openapi_definitions_dir()
    yaml_files = []

    for filename in os.listdir(openapi_dir):
        if filename.endswith('.yaml') or filename.endswith('.yml'):
            file_path = os.path.join(openapi_dir, filename)
            # Use filename without extension as identifier
            name = os.path.splitext(filename)[0]
            yaml_files.append((name, file_path))

    if not yaml_files:
        print(f"⚠️  No YAML files found in {openapi_dir}")

    return sorted(yaml_files)

# Load configuration when module is imported
_config = load_config()

# Export configuration values for backward compatibility
BASE_PACKAGE = _config['java']['base_package']
JAVA_FOLDER = _config['java']['java_folder']
EXAMPLES_FOLDER = _config['json']['examples_folder']
ENABLE_JAVADOC = _config['java']['enable_javadoc']
ENABLE_IMPORTS = _config['java']['enable_imports']
DETECT_PACKAGE = _config['java']['detect_package']

