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
    'openapi_file': 'openapi.yaml'
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
# This file is auto-generated and can be customized

# JSON Examples Configuration
json:
  # Output folder for generated JSON examples
  examples_folder: examples

# Java Code Generation Configuration
java:
  # Base package name for generated Java classes
  base_package: com.java
  
  # Output folder for generated Java classes
  java_folder: java
  
  # Enable or disable JavaDoc generation for classes and fields
  enable_javadoc: true
  
  # Enable or disable imports for referenced classes
  # If true, classes will import all necessary dependencies
  # If false, classes use simple names without imports 
  enable_imports: true
  
  # Enable or disable dynamic package detection based on folder structure
  # If true, package names will reflect the folder structure (e.g., com.java.POST_claim.body.related)
  # If false, all classes use the same base package (e.g., com.java)
  # Note: This only works when enable_imports is true
  detect_package: true

# OpenAPI specification file
openapi_file: openapi.yaml
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

# Load configuration when module is imported
config = load_config()

# Export configuration values
BASE_PACKAGE = config['java']['base_package']
JAVA_FOLDER = config['java']['java_folder']
EXAMPLES_FOLDER = config['json']['examples_folder']
OPENAPI_FILE = config['openapi_file']
ENABLE_JAVADOC = config['java']['enable_javadoc']
ENABLE_IMPORTS = config['java']['enable_imports']
DETECT_PACKAGE = config['java']['detect_package']

