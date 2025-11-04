# OpenAPI to Java Spring Classes Generator

Automated tool to convert OpenAPI YAML specifications into Java Spring classes with Lombok annotations. Features intelligent inheritance detection and clean code generation.

## Overview

**Two-step process:**
1. Extract JSON examples from OpenAPI endpoints (organized by METHOD_endpoint/body|response/related)
2. Generate Java Spring classes from JSON examples (same organization structure)

**Organization Strategy:**
- Examples and classes are organized by API endpoints
- Each endpoint folder contains `body/` and/or `response/` subdirectories
- Main schema is at the top level, all dependencies in `related/` subfolder
- Classes that appear in multiple endpoints are duplicated (no shared folder)
- All packages remain as `com.java` (imports not modified)

## Key Features

✅ **Endpoint-Based Organization** - Files organized by API endpoints (METHOD_endpoint/body|response/related)  
✅ **Smart Inheritance Detection** - Automatically detects `allOf` patterns in OpenAPI  
✅ **OneOf Polymorphism Support** - Uses class-level generics with bounded type parameters  
✅ **Complete Dependency Trees** - All related classes (including polymorphic children) in related/ folder  
✅ **Separate File Generation** - Each class in its own file (no nested static classes)  
✅ **CamelCase Preservation** - Maintains proper Java naming conventions  
✅ **Clean Code** - No JSON annotations, pure Lombok POJOs  
✅ **Full Reference Resolution** - Handles `$ref`, `allOf`, `oneOf`, `anyOf`  
✅ **Type Safety** - Proper generic types for Lists and nested objects  
✅ **Configurable** - All paths and package names configurable via `config.yaml`  
✅ **JavaDoc Documentation** - Classes and fields include JavaDoc with descriptions from OpenAPI schema  
✅ **Required Field Indicators** - Fields marked as required in OpenAPI include `@required` tag in JavaDoc  

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
```
## Quick Start

### Step 0: Prepare OpenAPI Specification & Configuration

1. **OpenAPI File**: Ensure your `openapi.yaml` file is complete and placed in the project root (or specify a different path in `config.yaml`)

2. **Configuration**: On first run, `config.yaml` will be created automatically with default values. You can customize it if needed.

```
OpenApi2Java/
├── openapi.yaml              ← YOUR OpenAPI SPECIFICATION (REQUIRED)
├── config.yaml               ← AUTO-GENERATED configuration (customizable)
├── config.yaml.example       ← Example configuration (for reference)
├── openapi.yaml.template     ← Template/example (for reference only)
├── config.py                 ← Configuration module
├── main.py                   ← Main execution script
├── generate_json_examples.py
├── generate_java_classes.py
└── README.md
```

**Quick Start:**
- If you have an existing OpenAPI spec: Place it as `openapi.yaml` in the root (or configure path in `config.yaml`)
- If starting from scratch: Use `openapi.yaml.template` as a reference
- Configuration is automatic: `config.yaml` is created on first run with sensible defaults

Example minimal `openapi.yaml` structure:
```yaml
openapi: 3.0.1
info:
  title: Your API
  version: "1.0"
paths:
  /claim:
    post:
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ClaimDetail'
      responses:
        '201':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ClaimCreate'
components:
  schemas:
    ClaimDetail:
      type: object
      properties:
        policyId:
          type: string
        claimDamagesSpecific:
          oneOf:
            - $ref: '#/components/schemas/ApplianceDamagesInfo'
            - $ref: '#/components/schemas/WaterDamagesInfo'
```

### Step 1: Generate JSON Examples

```bash
python generate_json_examples.py
```

**Output:** JSON examples organized by endpoint in `examples/`:

```
examples/
  POST_claim/
    body/
      ClaimDetail.json                    ← Main request body
      related/
        ClaimDamagesSpecific.json
        ApplianceDamagesInfo.json
        WaterDamagesInfo.json
        ClaimCaller.json
        ...
    response/
      ClaimCreate.json                    ← Main response
      related/
        ...
  GET_claim/
    response/
      Claim.json
      related/
        ...
```

### Step 2: Generate Java Classes

```bash
python generate_java_classes.py
# Select option 3 for manual generation
```

**Output:** Java files in `java/` with same structure:

```
java/
  POST_claim/
    body/
      ClaimDetail.java                    ← Main request class
      related/
        ClaimDamagesSpecific.java         ← Polymorphic base
        ApplianceDamagesInfo.java         ← Implementation 1
        WaterDamagesInfo.java             ← Implementation 2
        ClaimCaller.java
        ClaimOcurrenceAddress.java
        Damage.java
        AvailabilitiesRecord.java
        ...                               ← ALL dependencies
    response/
      ClaimCreate.java
  GET_claim/
    response/
      Claim.java
      related/
        ClaimBase.java
        ...
```

**Note:** Classes used in multiple endpoints are duplicated in each endpoint folder.

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

/**
 * Owner information.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Owner {
    /**
     * First name of the owner.
     *
     * @required This field is required
     */
    private String firstName;
    /**
     * Last name of the owner.
     *
     * @required This field is required
     */
    private String lastName;
    /**
     * Owner's address.
     */
    private Address address;
    /**
     * List of contact methods.
     */
    private List<ContactMethod> contactMethods;
}
```

**Note:** Fields and classes include JavaDoc documentation extracted from the OpenAPI schema descriptions. Fields marked as `required` include the `@required` tag in their JavaDoc.

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

### OneOf Support (Polymorphic Fields)
When your OpenAPI schema uses `oneOf`, the generator creates:
1. An abstract base class using the field name (e.g., `paymentMethod` → `PaymentMethod`)
2. Makes all specific types extend from that base class
3. Uses class-level generics with bounded type parameters

```java
package com.java;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Payment<TPaymentMethod extends PaymentMethod> {
    private String paymentId;
    private Double amount;
    // Can be one of: CreditCardInfo, BankAccountInfo, PayPalInfo, CryptoWalletInfo
    private TPaymentMethod paymentMethod;
}
```

**Generated base class:**
```java
package com.java;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public abstract class PaymentMethod {
    // Polymorphic base class for oneOf types
    // All concrete implementations will extend this class
}
```

**Specific implementation example:**
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
public class CreditCardInfo extends PaymentMethod {
    private String cardNumber;
    private String expirationDate;
    private String cvv;
}
```

**OpenAPI schema example:**
```yaml
components:
  schemas:
    Payment:
      type: object
      properties:
        paymentId:
          type: string
        amount:
          type: number
        paymentMethod:
          oneOf:
            - $ref: '#/components/schemas/CreditCardInfo'
            - $ref: '#/components/schemas/BankAccountInfo'
            - $ref: '#/components/schemas/PayPalInfo'
            - $ref: '#/components/schemas/CryptoWalletInfo'
```

**Usage example:**
```java
// Type-safe usage with specific implementation
Payment<CreditCardInfo> cardPayment = Payment.<CreditCardInfo>builder()
    .paymentId("PAY-001")
    .amount(99.99)
    .paymentMethod(new CreditCardInfo("1234-5678-9012-3456", "12/25", "123"))
    .build();

// Or with any other type that extends PaymentMethod
Payment<BankAccountInfo> bankPayment = Payment.<BankAccountInfo>builder()
    .paymentId("PAY-002")
    .amount(150.00)
    .paymentMethod(new BankAccountInfo("ES1234567890", "John Doe"))
    .build();
```

### Required Fields and JavaDoc

All generated classes include JavaDoc documentation. Fields with descriptions in the OpenAPI schema include field-level JavaDoc. Fields marked as `required` in the OpenAPI schema are automatically annotated with the `@required` tag in their JavaDoc. This provides clear, professional documentation while maintaining type safety.

**OpenAPI schema example:**
```yaml
MessageDetail:
  description: Object that encapsulates the information of the message related to a proceed.
  required:
    - name
    - messageText
  type: object
  properties:
    name:
      type: string
      description: Full name of sender.
    messageText:
      type: string
      description: Text of the message.
    contact:
      $ref: "#/components/schemas/MessageContact"
    address:
      $ref: "#/components/schemas/MessageAddress"
```

**Generated Java class:**
```java
/**
 * Object that encapsulates the information of the message related to a proceed.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MessageDetail {
    /**
     * Full name of sender.
     * @required This field is required
     */
    private String name;
    private MessageContact contact;
    private MessageAddress address;
    /**
     * Text of the message.
     * @required This field is required
     */
    private String messageText;
}
```

**Features:**
- **Class-level JavaDoc**: Generated from the schema's `description` field
- **Field-level JavaDoc**: Generated from each property's `description` field (only if description exists or field is required)
- **@required tag**: Automatically added to required fields' JavaDoc
- **OneOf documentation**: Polymorphic fields include "Can be one of: ..." in their JavaDoc
- **Long descriptions**: Automatically wrapped at 100 characters for readability
- **Clean formatting**: No unnecessary blank lines in JavaDoc

**Note:** 
- JavaDoc is only generated for fields that have a description in the OpenAPI schema OR are marked as required
- Fields without description and not required will not have JavaDoc
- The `@required` tag only appears for fields explicitly listed in the `required` array of the OpenAPI schema
- This includes direct required fields and required fields defined within `allOf` blocks

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

**Four-pass generation:**

1. **Pass 1: Analyze OpenAPI**
   - Load inheritance from `allOf` patterns
   - Detect `oneOf` fields for polymorphic type handling
   - Extract required fields from schema definitions
   - Build schema relationship map
   - No naming conventions required

2. **Pass 2: Generate Classes**
   - Create all top-level classes
   - Extract nested objects to separate files
   - Apply generic `Object` type to `oneOf` fields with type comments
   - Add `// Required` comments to mandatory fields
   - Maintain type references

3. **Pass 3: Apply Inheritance**
   - Regenerate classes with base classes
   - Add `@EqualsAndHashCode(callSuper = true)`
   - Filter inherited fields
   - Preserve required field indicators

4. **Pass 4: Organize by Domain**
   - Group classes into endpoint folders (body/response)
   - Create related/ subfolders for dependencies
   - Further organize by inheritance hierarchies

## Configuration

The generator uses a `config.yaml` file for configuration. This file is **automatically created** with default values when you run `main.py` for the first time.

### Configuration File (`config.yaml`)

The configuration file is in `.gitignore` and allows you to customize:

```yaml
# OpenAPI to Java Generator Configuration
# This file is auto-generated and can be customized

# Base package name for generated Java classes
base_package: com.java

# Output folder for generated Java classes
java_folder: java

# Output folder for generated JSON examples
examples_folder: examples

# OpenAPI specification file
openapi_file: openapi.yaml
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `base_package` | `com.java` | Base package name for all generated Java classes |
| `java_folder` | `java` | Output directory for generated Java classes |
| `examples_folder` | `examples` | Output directory for generated JSON examples |
| `openapi_file` | `openapi.yaml` | Path to your OpenAPI specification file |

### How to Customize Configuration

1. **First run**: When you execute `main.py`, `config.yaml` is created automatically with default values
2. **Customize**: Edit `config.yaml` to match your project structure
3. **Version control**: The file is in `.gitignore`, so each developer can have their own configuration

**Example custom configuration:**
```yaml
base_package: com.mycompany.api.models
java_folder: src/main/java/com/mycompany/api/models
examples_folder: target/examples
openapi_file: specifications/my-api.yaml
```

### Using Configuration in Scripts

All scripts (`main.py`, `generate_json_examples.py`, `generate_java_classes.py`) automatically load configuration from `config.yaml`:

```python
from config import BASE_PACKAGE, JAVA_FOLDER, EXAMPLES_FOLDER, OPENAPI_FILE
```

The configuration module:
- ✅ Auto-creates `config.yaml` if it doesn't exist
- ✅ Validates and merges with default values
- ✅ Provides configuration as importable constants
- ✅ Shows helpful messages when creating defaults

## Legacy Configuration (Deprecated)

### `generate_json_examples.py`
```python
# Old way (hardcoded)
openapi_file_path = 'openapi.yaml'
output_directory = 'examples'

# New way (from config.yaml)
from config import OPENAPI_FILE, EXAMPLES_FOLDER
```

### `generate_java_classes.py`
```python
# Old way (hardcoded)
examples_directory = 'examples'
output_directory = 'java'
package_name = 'com.java'

# New way (from config.yaml)
from config import EXAMPLES_FOLDER, JAVA_FOLDER, BASE_PACKAGE
```

## How to Use

### Running the Main Script

The `main.py` script automates the entire process of generating examples and Java classes. It ensures that the OpenAPI file exists (as specified in `config.yaml`), deletes old output folders, and regenerates them.

```bash
python3 main.py
```

### What the Script Does
1. Loads configuration from `config.yaml` (creates it with defaults if it doesn't exist)
2. Checks if the OpenAPI file exists (from configuration)
3. Deletes the output folders if they exist (from configuration)
4. Runs `generate_json_examples.py` to create JSON examples
5. Runs `generate_java_classes.py` to generate Java classes from OpenAPI schema

### Output Structure
- `java/` - Contains generated Java classes organized by endpoints.
- `examples/` - Contains JSON examples organized by endpoints.