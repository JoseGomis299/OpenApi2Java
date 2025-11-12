# OpenAPI to Java Spring Classes Generator

Automated tool to convert OpenAPI YAML specifications into Java Spring classes with Lombok annotations and Spring Cloud OpenFeign clients. Features intelligent inheritance detection, clean code generation, and automatic API client generation.

## Overview

**Three-step process:**
1. Extract JSON examples from OpenAPI endpoints (organized by METHOD_endpoint/body|response/related)
2. Generate Java Spring classes from JSON examples (same organization structure)
3. Generate Spring Cloud OpenFeign client interfaces from OpenAPI specification

**Organization Strategy:**
- Examples and classes are organized by API endpoints
- Each endpoint folder contains `body/` and/or `response/` subdirectories
- Main schema is at the top level, all dependencies in `related/` subfolder
- Classes that appear in multiple endpoints are duplicated (no shared folder)
- Feign clients are organized by OpenAPI tags in a separate folder
- All packages remain as `com.java` (imports not modified)

## Key Features

✅ **Endpoint-Based Organization** - Files organized by API endpoints (METHOD_endpoint/body|response/related)  
✅ **ALL_SCHEMAS Folder** - Consolidated view of all unique schemas organized by inheritance hierarchy  
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
✅ **Feign Client Generation** - Automatic Spring Cloud OpenFeign client interfaces with proper annotations  
✅ **Tag-Based Client Organization** - One Feign client per OpenAPI tag (e.g., Claim, Proceeding, Document)  
✅ **Generic Types with Wildcards** - Schemas with oneOf properties generate generic types (e.g., `ClaimDetail<? extends ClaimDamagesSpecific>`)  
✅ **Parameter Filtering** - Configurable parameter exclusion in Feign clients (optional params, specific params)  

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

### Step 0: Prepare OpenAPI Specifications & Configuration

1. **OpenAPI Files**: Place your OpenAPI YAML files in the `openApiDefinitions/` directory
   - The tool processes all `.yaml` and `.yml` files in this directory
   - Each definition generates output in its own subdirectory
   - Example: `openApiDefinitions/my-api.yaml` → `feign/my-api/`, `java/my-api/`, `examples/my-api/`

2. **Configuration**: On first run, `config.yaml` will be created automatically with default values

```
OpenApi2Java/
├── openApiDefinitions/           ← YOUR OpenAPI YAML FILES (auto-created)
│   ├── my-api.yaml
│   ├── another-api.yaml
│   └── ...
├── config.yaml                   ← Configuration (auto-generated)
├── config.py                     ← Configuration module
├── main.py                       ← Main execution script
├── generate_json_examples.py
├── generate_java_classes.py
├── generate_feign_clients.py
└── README.md
```

**Quick Start:**
- Run any script once to auto-create the `openApiDefinitions/` directory
- Add your OpenAPI YAML files to `openApiDefinitions/`
- Each file will be processed independently
- Configuration is automatic: `config.yaml` is created on first run

Example minimal OpenAPI file structure:
```yaml
openapi: 3.0.1
info:
  title: Your API
  version: "1.0"
paths:
  /example:
    get:
      tags:
        - Example
      responses:
        '200':
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
```components:
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

The generator uses a `config.yaml` file for configuration. This file is **automatically created** with default values when you run any script for the first time.

### Configuration File (`config.yaml`)

Example configuration:

```yaml
json:
  examples_folder: examples

java:
  base_package: com.mycompany.api.model
  java_folder: java
  enable_javadoc: true
  enable_imports: true
  detect_package: true

openapi_definitions_dir: openApiDefinitions

feign:
  base_package: com.mycompany.api.client
  feign_folder: feign
  enable_javadoc: true
  interface_suffix: Client
  generate_config: true
  grouping_strategy: single-client
  use_response_entity: false
  format_one_param_per_line: true
  add_feign_annotation: true
```

### Configuration Options

#### JSON Examples

| Option | Default | Description |
|--------|---------|-------------|
| `json.examples_folder` | `examples` | Output directory for generated JSON examples |

#### Java Classes

| Option | Default | Description |
|--------|---------|-------------|
| `java.base_package` | `com.java` | Base package name for all generated Java classes |
| `java.java_folder` | `java` | Output directory for generated Java classes |
| `java.enable_javadoc` | `true` | Enable JavaDoc generation for classes and fields |
| `java.enable_imports` | `true` | Enable imports for referenced classes. If false, uses simple names |
| `java.detect_package` | `true` | Dynamic package detection based on folder structure. Only works when `enable_imports` is true |

#### OpenAPI Definitions

| Option | Default | Description |
|--------|---------|-------------|
| `openapi_definitions_dir` | `openApiDefinitions` | Directory containing OpenAPI YAML files to process |

#### Feign Clients

| Option | Default | Description |
|--------|---------|-------------|
| `feign.base_package` | `com.java.client` | Base package for Feign client interfaces |
| `feign.feign_folder` | `feign` | Output directory for Feign clients |
| `feign.enable_javadoc` | `true` | Generate JavaDoc for interfaces and methods |
| `feign.interface_suffix` | `Client` | Suffix for interface names (e.g., `APIClaimHomeClient`) |
| `feign.generate_config` | `true` | Generate FeignConfiguration class with common settings |
| `feign.grouping_strategy` | `single-client` | `single-client`: One interface with all endpoints grouped by tag comments<br>`by-tag`: Separate interface per tag |
| `feign.use_response_entity` | `false` | Wrap return types in `ResponseEntity<T>`. If false, returns type directly |
| `feign.format_one_param_per_line` | `true` | Format method parameters with one per line for readability |
| `feign.add_feign_annotation` | `true` | Add `@FeignClient` annotation to generated interfaces |
| `feign.ignore_optional_params` | `false` | Skip all optional (non-required) parameters from method signatures |
| `feign.ignore_params_list` | `[]` | List of specific parameter names to exclude (e.g., `['X-Request-processId', 'Accept-Language']`) |

### Grouping Strategies Explained

#### single-client (Recommended)
Generates a single interface containing all API endpoints, organized with comment separators by tag:

```java
public interface APIClaimHomeClient {
    
    // ========================================
    // Claim
    // ========================================
    
    @GetMapping("/claim/{id}")
    Claim getClaim(@PathVariable("id") String id);
    
    // ========================================
    // Document
    // ========================================
    
    @PostMapping("/document")
    Document createDocument(@RequestBody DocumentRequest body);
}
```

#### by-tag
Generates separate interfaces for each OpenAPI tag:
- `ClaimClient.java` - Only claim operations
- `DocumentClient.java` - Only document operations
- etc.

### Parameter Filtering

The Feign client generator allows you to exclude parameters from method signatures using two mechanisms:

#### 1. Ignore Optional Parameters

Set `ignore_optional_params: true` to exclude all non-required parameters:

```yaml
feign:
  ignore_optional_params: true
```

**Before:**
```java
@GetMapping("/claim/{id}")
Claim getClaim(
    @PathVariable("id") String id,
    @RequestHeader("Accept-Language") String acceptLanguage,
    @RequestHeader(value = "X-Request-processId", required = false) String xRequestProcessid
);
```

**After:**
```java
@GetMapping("/claim/{id}")
Claim getClaim(
    @PathVariable("id") String id,
    @RequestHeader("Accept-Language") String acceptLanguage
);
```

#### 2. Ignore Specific Parameters

Use `ignore_params_list` to exclude specific parameters by name:

```yaml
feign:
  ignore_params_list:
    - X-Request-processId
    - Accept-Language
    - X-Debug-Mode
```

**Before:**
```java
@GetMapping("/claim/{id}")
Claim getClaim(
    @PathVariable("id") String id,
    @RequestHeader("Accept-Language") String acceptLanguage,
    @RequestHeader("X-Request-applicationId") String xRequestApplicationid,
    @RequestHeader(value = "X-Request-processId", required = false) String xRequestProcessid
);
```

**After:**
```java
@GetMapping("/claim/{id}")
Claim getClaim(
    @PathVariable("id") String id,
    @RequestHeader("X-Request-applicationId") String xRequestApplicationid
);
```

**Use Cases:**
- Remove logging/tracing headers handled by interceptors
- Exclude optional parameters that have sensible defaults
- Simplify client interfaces by removing rarely-used parameters
- Clean up legacy parameters that are no longer needed

**Note:** Both filtering options can be used together. The tool will skip a parameter if:
- It appears in `ignore_params_list`, OR
- It's optional AND `ignore_optional_params` is true

### How to Customize Configuration

1. **First run**: Execute any script to auto-create `config.yaml`
2. **Customize**: Edit the generated file to match your project structure
3. **Apply**: Re-run the scripts to regenerate with new settings
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
openapi_file_path = 'openApiDefinitions/claim-home.yaml'
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
6. Runs `generate_feign_clients.py` to generate Spring Cloud OpenFeign client interfaces

### Output Structure
- `java/` - Contains generated Java classes organized by endpoints
  - `<api-name>/` - Subdirectory per OpenAPI definition
    - `GET_endpoint/`, `POST_endpoint/`, etc. - Endpoint-specific classes
    - `NO_ENDPOINT/` - Schemas not used in any endpoint
    - `ALL_SCHEMAS/` - **NEW**: All unique schemas organized by inheritance
- `examples/` - Contains JSON examples organized by endpoints
  - `<api-name>/` - Subdirectory per OpenAPI definition
    - `GET_endpoint/`, `POST_endpoint/`, etc. - Endpoint-specific examples
    - `ALL_SCHEMAS/` - **NEW**: All unique schema examples organized by inheritance
- `feign/` - Contains generated Feign client interfaces
  - `<api-name>/` - Subdirectory per OpenAPI definition

### ALL_SCHEMAS Folder

**New Feature**: Both JSON examples and Java classes now generate an `ALL_SCHEMAS` folder containing all unique schemas organized by inheritance hierarchy.

**Structure:**
```
ALL_SCHEMAS/
├── BaseSchema1.json (or .java)
├── BaseSchema2.json (or .java)
├── BaseSchema1/
│   ├── DerivedSchema1.json (or .java)
│   └── DerivedSchema2.json (or .java)
└── BaseSchema2/
    └── DerivedSchema3.json (or .java)
```

**Benefits:**
- **Consolidated View**: All schemas in one place
- **No Duplicates**: Each schema appears only once
- **Clear Hierarchy**: Inheritance relationships visible in folder structure
- **Easy Navigation**: Find base classes and their derivatives instantly

**Example:**
```
java/claim-home-catalog/ALL_SCHEMAS/
├── Error.java                    # Base class
├── PatrimonialAvailability.java  # Base class
├── Error/
│   ├── ErrorComponent.java       # Extends Error
│   └── ErrorInfo.java             # Extends Error
└── AvailabilityResponse.java     # Base class
```

## Feign Client Generation

The generator now includes automatic creation of Spring Cloud OpenFeign client interfaces based on your OpenAPI specification. This eliminates the need to manually write HTTP client code.

### What are Feign Clients?

Spring Cloud OpenFeign is a declarative HTTP client framework that makes writing HTTP clients easier. Instead of manually implementing REST clients with RestTemplate or WebClient, you simply define an interface with annotations, and Feign handles the implementation.

### Generated Feign Clients

#### Standalone Generation

You can generate only Feign clients without running the full pipeline:

```bash
python3 generate_feign_clients.py
```

#### Features

- **Tag-Based Organization**: One Feign client interface per OpenAPI tag (e.g., ClaimClient, ProceedingClient, DocumentClient)
- **Spring Annotations**: Proper `@FeignClient`, `@GetMapping`, `@PostMapping`, etc.
- **Type-Safe Parameters**: All path variables, query params, headers, and request bodies
- **ResponseEntity Wrappers**: All methods return `ResponseEntity<T>` for proper HTTP handling
- **JavaDoc Documentation**: Includes summaries and descriptions from OpenAPI
- **Configuration Class**: Optional FeignConfiguration class with common settings

#### Example Generated Feign Client

**OpenAPI Definition:**
```yaml
paths:
  /claim/{claimId}:
    get:
      tags:
        - Claim
      summary: Get a certain claim.
      description: Get a certain claim, given its unique claim ID.
      operationId: getClaimHome
      parameters:
        - name: claimId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Claim"
```

**Generated Feign Client:**
```java
package com.mapfresaluddigital.apichannelhome.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;

/**
 * Feign client for Claim operations.
 * Business API containing claim/assistance opening and management operations for Spain.
 */
@FeignClient(name = "claim", url = "${feign.client.claim.url}")
public interface ClaimClient {

    /**
     * Get a certain claim.
     * Get a certain claim, given its unique claim ID.
     *
     * @param claimId
     * @return Claim
     */
    @GetMapping("/claim/{claimId}")
    ResponseEntity<Claim> getClaimHome(@PathVariable("claimId") String claimId);

    /**
     * Generate claim.
     * Generate claim.
     *
     * @param body
     * @return ClaimCreate
     */
    @PostMapping("/claim")
    ResponseEntity<ClaimCreate> generateClaimPatrimonial(@RequestBody ClaimDetail body);
}
```

### Configuration

Feign client generation is fully configurable via `config.yaml`:

```yaml
# Feign Client Generation Configuration
feign:
  # Base package name for generated Feign clients
  base_package: com.mapfresaluddigital.apichannelhome.client
  
  # Output folder for generated Feign clients
  feign_folder: feign
  
  # Enable or disable JavaDoc generation for Feign interfaces and methods
  enable_javadoc: true
  
  # Suffix to append to interface names (e.g., ClaimClient)
  interface_suffix: Client
  
  # Generate FeignConfiguration classes
  generate_config: true
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `base_package` | `com.java.client` | Base package for Feign client interfaces |
| `feign_folder` | `feign` | Output directory for Feign clients |
| `enable_javadoc` | `true` | Generate JavaDoc for interfaces and methods |
| `interface_suffix` | `Client` | Suffix for interface names (e.g., ClaimClient) |
| `generate_config` | `true` | Generate FeignConfiguration class |

### Using Generated Feign Clients

1. **Add Spring Cloud OpenFeign Dependency** (Maven):
```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-openfeign</artifactId>
</dependency>
```

2. **Enable Feign Clients** in your Spring Boot application:
```java
@SpringBootApplication
@EnableFeignClients(basePackages = "com.mapfresaluddigital.apichannelhome.client")
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

3. **Configure Base URLs** in `application.yml`:
```yaml
feign:
  client:
    claim:
      url: https://api.example.com/api/v1
    proceeding:
      url: https://api.example.com/api/v1
    document:
      url: https://api.example.com/api/v1
```

4. **Inject and Use** in your services:
```java
@Service
public class ClaimService {
    
    private final ClaimClient claimClient;
    
    public ClaimService(ClaimClient claimClient) {
        this.claimClient = claimClient;
    }
    
    public Claim getClaim(String claimId) {
        ResponseEntity<Claim> response = claimClient.getClaimHome(claimId);
        return response.getBody();
    }
    
    public ClaimCreate createClaim(ClaimDetail details) {
        ResponseEntity<ClaimCreate> response = claimClient.generateClaimPatrimonial(details);
        return response.getBody();
    }
}
```

### Generated FeignConfiguration

When `generate_config: true`, a configuration class is created:

```java
package com.mapfresaluddigital.apichannelhome.client.config;

import feign.Logger;
import feign.RequestInterceptor;
import feign.codec.ErrorDecoder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Common Feign client configuration.
 */
@Configuration
public class FeignConfiguration {

    /**
     * Set Feign logging level.
     */
    @Bean
    public Logger.Level feignLoggerLevel() {
        return Logger.Level.FULL;
    }

    /**
     * Custom error decoder for Feign clients.
     */
    @Bean
    public ErrorDecoder errorDecoder() {
        return new ErrorDecoder.Default();
    }
}
```

This provides a central place to configure:
- Logging levels
- Error handling
- Request/response interceptors
- Custom encoders/decoders

### Output Structure
```
feign/
  ClaimClient.java
  ProceedingClient.java
  CommunicationClient.java
  IndemnityClient.java
  DocumentClient.java
  TaskClient.java
  AssistanceClient.java
  config/
    FeignConfiguration.java
```
