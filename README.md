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
✅ **No Import Changes** - All packages remain as `com.java`  

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
   - Detect `oneOf` fields for polymorphic type handling
   - Build schema relationship map
   - No naming conventions required

2. **Pass 2: Generate Classes**
   - Create all top-level classes
   - Extract nested objects to separate files
   - Apply generic `Object` type to `oneOf` fields with type comments
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

## How to Use

### Running the Main Script

The `main.py` script automates the entire process of generating examples and Java classes. It ensures that the `openapi.yaml` file exists, deletes old `java` and `examples` folders, and regenerates them.

```bash
python3 main.py
```

### What the Script Does
1. Checks if `openapi.yaml` exists in the root directory.
2. Deletes the `java` and `examples` folders if they exist.
3. Runs `generate_json_examples.py` to create JSON examples.
4. Runs `generate_java_classes.py` to generate Java classes from the examples.

### Output Structure
- `java/` - Contains generated Java classes organized by endpoints.
- `examples/` - Contains JSON examples organized by endpoints.
