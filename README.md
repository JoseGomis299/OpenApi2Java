# OpenAPI to Java Spring Classes Generator

Automated tool to convert OpenAPI YAML specifications into Java Spring classes with Lombok annotations. Features intelligent inheritance detection and clean code generation.

## Overview

**Two-step process:**
1. Extract JSON examples from OpenAPI schema definitions
2. Generate Java Spring classes from JSON examples

## Key Features

✅ **Smart Inheritance Detection** - Automatically detects `allOf` patterns in OpenAPI  
✅ **Separate File Generation** - Each class in its own file (no nested static classes)  
✅ **CamelCase Preservation** - Maintains proper Java naming conventions  
✅ **Clean Code** - No JSON annotations, pure Lombok POJOs  
✅ **Full Reference Resolution** - Handles `$ref`, `allOf`, `oneOf`, `anyOf`  
✅ **Type Safety** - Proper generic types for Lists and nested objects  

## Prerequisites

### 1. OpenAPI Specification File

**⚠️ IMPORTANT:** You must have a complete `openapi.yaml` file in the project root directory before running the scripts.

The `openapi.yaml` file should contain:
- Complete schema definitions in `components/schemas`
- Proper type definitions for all models
- `allOf` patterns for inheritance relationships (if needed)

### 2. Python Dependencies

**Required:** Install PyYAML before running the scripts

```bash
# Install PyYAML for YAML file parsing
pip install pyyaml

# Or with pip3
pip3 install pyyaml

# Or for specific Python version
python3.14 -m pip install pyyaml
```


```bash
# quicktype for advanced generation 
npm install -g quicktype
```
## Quick Start

### Step 0: Prepare OpenAPI Specification

Ensure your `openapi.yaml` file is complete and placed in the project root:

```
OpenApi2Java/
├── openapi.yaml              ← YOUR OpenAPI SPECIFICATION (REQUIRED)
├── openapi.yaml.template     ← Template/example (for reference only)
├── generate_json_examples.py
├── generate_java_classes.py
└── README.md
```

**Quick Start:**
- If you have an existing OpenAPI spec: Place it as `openapi.yaml` in the root
- If starting from scratch: Use `openapi.yaml.template` as a reference

Example minimal `openapi.yaml` structure:
```yaml
openapi: 3.0.1
info:
  title: Your API
  version: "1.0"
components:
  schemas:
    YourModel:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
```

### Step 1: Generate JSON Examples

```bash
python generate_json_examples.py
```

**Output:** JSON examples in `examples/` directory

### Step 2: Generate Java Classes

```bash
python generate_java_classes.py
# Select option 3 for manual generation
```

**Output:** Java files in `java/`

## Generated Code Examples

### Parent Class with Inheritance
```java
package com.java;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

@Data
@EqualsAndHashCode(callSuper = true)
@NoArgsConstructor
@AllArgsConstructor
public class Car extends Vehicle {
    private Engine engine;
    private Owner owner;
}
```

### Nested Class as Separate File
```java
package com.java;

import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Owner {
    private String firstName;
    private String lastName;
    private Address address;
    private List<ContactMethod> contactMethods;
}
```

### Base Class
```java
package com.java;

import java.time.LocalDateTime;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Vehicle {
    private String vehicleId;
    private String brand;
    private String model;
    private LocalDateTime manufacturingDate;
    private Integer numberOfDoors;
}
```

## How It Works

### JSON Generation (`generate_json_examples.py`)

1. Loads OpenAPI YAML specification
2. Resolves all `$ref` references recursively
3. Handles schema composition (`allOf`, `oneOf`, `anyOf`)
4. Generates realistic example data
5. Creates one JSON file per schema

**Key features:**
- Property-level reference resolution
- Circular reference detection
- Array type handling in `allOf`
- Dependency tree visualization

### Java Generation (`generate_java_classes.py`)

**Three-pass generation:**

1. **Pass 1: Analyze OpenAPI**
   - Load inheritance from `allOf` patterns
   - Build schema relationship map
   - No naming conventions required

2. **Pass 2: Generate Classes**
   - Create all top-level classes
   - Extract nested objects to separate files
   - Maintain type references

3. **Pass 3: Apply Inheritance**
   - Regenerate classes with base classes
   - Add `@EqualsAndHashCode(callSuper = true)`
   - Filter inherited fields

## Configuration

### Required: `openapi.yaml`

**This file must be created/provided by you** and placed in the project root. It should contain your complete OpenAPI specification.

### `generate_json_examples.py`
```python
openapi_file_path = 'openapi.yaml'  # Path to your OpenAPI specification
output_directory = 'examples'        # Where JSON examples will be saved
```

### `generate_java_classes.py`
```python
examples_directory = 'examples'                              # Input: JSON examples
output_directory = 'java' # Output: Java files
package_name = 'com.java' # Java package name
```