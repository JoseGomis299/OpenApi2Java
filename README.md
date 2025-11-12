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
✅ **Smart Inheritance Detection** - Automatically detects `allOf` patterns and generates proper class hierarchies  
✅ **OneOf Polymorphism Support** - Generic types with bounded parameters for polymorphic fields  
✅ **Clean Lombok POJOs** - One class per file, no JSON annotations, proper separation of concerns  
✅ **Feign Client Generation** - Automatic Spring Cloud OpenFeign client interfaces from OpenAPI  
✅ **Full Configurability** - All paths, packages, and generation behavior via `config.yaml`  

## Prerequisites

### Python Dependencies

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
  title: Product API
  version: "1.0"
paths:
  /products/{id}:
    get:
      tags:
        - Product
      operationId: getProduct
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Product'
components:
  schemas:
    Product:
      type: object
      required:
        - id
        - name
        - price
      properties:
        id:
          type: string
          description: Unique product identifier
        name:
          type: string
          description: Product name
        price:
          type: number
          description: Product price
        category:
          type: string
          description: Product category
```

### Step 1: Generate JSON Examples

```bash
python generate_json_examples.py
```

**Output:** JSON examples organized by endpoint in `examples/`:

```
examples/
  POST_products/
    body/
      ProductRequest.json              ← Main request body
      related/
        Category.json
        Supplier.json
        PriceInfo.json
        ...
    response/
      ProductResponse.json             ← Main response
      related/
        ...
  GET_products/
    response/
      Product.json
      related/
        ...
  ALL_SCHEMAS/                         ← All unique schemas
    Product.json
    Category.json
    Supplier.json
    ...
```

### Step 2: Generate Java Classes

```bash
python generate_java_classes.py
```

**Output:** Java files in `java/` with same structure:

```
java/
  POST_products/
    body/
      ProductRequest.java              ← Main request class
      related/
        Category.java
        Supplier.java
        PriceInfo.java
        ...
    response/
      ProductResponse.java
  GET_products/
    response/
      Product.java
      related/
        ...
  ALL_SCHEMAS/                         ← All unique schemas organized by inheritance
    Product.java
    Category.java
    paymentMethod/
      PaymentMethod.java               ← Parent class
      CreditCard.java                  ← Child class
      BankTransfer.java                ← Child class
```

**Note:** Classes used in multiple endpoints are duplicated in each endpoint folder. ALL_SCHEMAS provides a consolidated view with inheritance organization.

## Generated Code Examples

### Parent Class with Inheritance
```java
package com.mycompany.api.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

/**
 * Car entity extending base Vehicle class.
 */
@Data
@EqualsAndHashCode(callSuper = true)
@NoArgsConstructor
@AllArgsConstructor
public class Car extends Vehicle {
    /**
     * Engine specifications.
     * @required This field is required
     */
    private Engine engine;
    
    /**
     * Car owner information.
     */
    private Owner owner;
}
```

### Nested Class as Separate File
```java
package com.mycompany.api.model;

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
     * @required This field is required
     */
    private String firstName;
    
    /**
     * Last name of the owner.
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
package com.mycompany.api.model;

import java.time.LocalDateTime;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Base vehicle information.
 */
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
package com.mycompany.api.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Payment transaction information.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Payment<TPaymentMethod extends PaymentMethod> {
    private String paymentId;
    private Double amount;
    /**
     * Can be one of: CreditCardInfo, BankAccountInfo, PayPalInfo, CryptoWalletInfo
     */
    private TPaymentMethod paymentMethod;
}
```

**Generated base class:**
```java
package com.mycompany.api.model;

import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Polymorphic base class for oneOf types.
 * All concrete implementations will extend this class.
 */
@Data
@NoArgsConstructor
public abstract class PaymentMethod {
}
```

**Specific implementation example:**
```java
package com.mycompany.api.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

/**
 * Credit card payment information.
 */
@Data
@EqualsAndHashCode(callSuper = true)
@NoArgsConstructor
@AllArgsConstructor
public class CreditCardInfo extends PaymentMethod {
    /**
     * Credit card number.
     * @required This field is required
     */
    private String cardNumber;
    
    /**
     * Card expiration date (MM/YY format).
     * @required This field is required
     */
    private String expirationDate;
    
    /**
     * Card verification value.
     * @required This field is required
     */
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
ContactMessage:
  description: Message information for customer contact.
  required:
    - senderName
    - messageText
  type: object
  properties:
    senderName:
      type: string
      description: Full name of the sender.
    messageText:
      type: string
      description: Content of the message.
    contactInfo:
      $ref: "#/components/schemas/ContactInfo"
    preferredContactTime:
      type: string
      description: Preferred time for contact response.
```

**Generated Java class:**
```java
package com.mycompany.api.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Message information for customer contact.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ContactMessage {
    /**
     * Full name of the sender.
     * @required This field is required
     */
    private String senderName;
    
    private ContactInfo contactInfo;
    
    /**
     * Preferred time for contact response.
     */
    private String preferredContactTime;
    
    /**
     * Content of the message.
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
public interface APIProductClient {
    
    // ========================================
    // Product
    // ========================================
    
    @GetMapping("/products/{id}")
    Product getProduct(@PathVariable("id") String id);
    
    // ========================================
    // Order
    // ========================================
    
    @PostMapping("/orders")
    Order createOrder(@RequestBody OrderRequest body);
}
```

#### by-tag
Generates separate interfaces for each OpenAPI tag:
- `ProductClient.java` - Only product operations
- `OrderClient.java` - Only order operations
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
@GetMapping("/products/{id}")
Product getProduct(
    @PathVariable("id") String id,
    @RequestHeader("Accept-Language") String acceptLanguage,
    @RequestHeader(value = "X-Request-TraceId", required = false) String xRequestTraceId
);
```

**After:**
```java
@GetMapping("/products/{id}")
Product getProduct(
    @PathVariable("id") String id,
    @RequestHeader("Accept-Language") String acceptLanguage
);
```

#### 2. Ignore Specific Parameters

Use `ignore_params_list` to exclude specific parameters by name:

```yaml
feign:
  ignore_params_list:
    - X-Request-TraceId
    - Accept-Language
    - X-Debug-Mode
```

**Before:**
```java
@GetMapping("/products/{id}")
Product getProduct(
    @PathVariable("id") String id,
    @RequestHeader("Accept-Language") String acceptLanguage,
    @RequestHeader("X-Request-ApplicationId") String xRequestApplicationId,
    @RequestHeader(value = "X-Request-TraceId", required = false) String xRequestTraceId
);
```

**After:**
```java
@GetMapping("/products/{id}")
Product getProduct(
    @PathVariable("id") String id,
    @RequestHeader("X-Request-ApplicationId") String xRequestApplicationId
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

### Using Configuration in Scripts

All scripts (`main.py`, `generate_json_examples.py`, `generate_java_classes.py`) automatically load configuration from `config.yaml`:

```python
from config import get_config, get_openapi_definition_files
```

The configuration module:
- ✅ Auto-creates `config.yaml` if it doesn't exist
- ✅ Validates and merges with default values
- ✅ Provides configuration as importable constants
- ✅ Shows helpful messages when creating defaults

## How to Use

### Running the Main Script

The `main.py` script automates the entire process of generating examples and Java classes. It ensures that the OpenAPI files exist, deletes old output folders, and regenerates them.

```bash
python main.py
```

### What the Script Does
1. Loads configuration from `config.yaml` (creates it with defaults if it doesn't exist)
2. Processes all OpenAPI YAML files in `openApiDefinitions/` directory
3. For each definition:
   - Deletes existing output folders if they exist
   - Runs `generate_json_examples.py` to create JSON examples
   - Runs `generate_java_classes.py` to generate Java classes from OpenAPI schema
   - Runs `generate_feign_clients.py` to generate Spring Cloud OpenFeign client interfaces

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
├── baseSchema1/
│   ├── BaseSchema1.json (or .java)      ← Parent class also in folder
│   ├── DerivedSchema1.json (or .java)
│   └── DerivedSchema2.json (or .java)
└── baseSchema2/
    ├── BaseSchema2.json (or .java)      ← Parent class also in folder
    └── DerivedSchema3.json (or .java)
```

**Benefits:**
- **Consolidated View**: All schemas in one place
- **No Duplicates**: Each schema appears only once
- **Clear Hierarchy**: Inheritance relationships visible in folder structure
- **Easy Navigation**: Find base classes and their derivatives instantly
- **Parent Classes Included**: Base classes are copied to their own folders along with children

**Example:**
```
java/product-api/ALL_SCHEMAS/
├── Product.java                   # Base class (also in root)
├── PaymentMethod.java             # Base class (also in root)
├── product/
│   ├── Product.java               # Parent class
│   ├── PhysicalProduct.java       # Extends Product
│   └── DigitalProduct.java        # Extends Product
├── paymentMethod/
│   ├── PaymentMethod.java         # Parent class
│   ├── CreditCard.java            # Extends PaymentMethod
│   └── BankTransfer.java          # Extends PaymentMethod
└── Category.java                  # Standalone class
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

- **Tag-Based Organization**: One Feign client interface per OpenAPI tag (e.g., ProductClient, OrderClient, CustomerClient)
- **Spring Annotations**: Proper `@FeignClient`, `@GetMapping`, `@PostMapping`, etc.
- **Type-Safe Parameters**: All path variables, query params, headers, and request bodies
- **ResponseEntity Wrappers**: Optional `ResponseEntity<T>` return types for proper HTTP handling
- **JavaDoc Documentation**: Includes summaries and descriptions from OpenAPI
- **Configuration Class**: Optional FeignConfiguration class with common settings

#### Example Generated Feign Client

**OpenAPI Definition:**
```yaml
paths:
  /products/{productId}:
    get:
      tags:
        - Product
      summary: Get product details
      description: Retrieve detailed information about a specific product.
      operationId: getProduct
      parameters:
        - name: productId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Product"
```

**Generated Feign Client:**
```java
package com.mycompany.api.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;

/**
 * Feign client for Product operations.
 * Product catalog API for managing products and inventory.
 */
@FeignClient(name = "product", url = "${feign.client.product.url}")
public interface ProductClient {

    /**
     * Get product details.
     * Retrieve detailed information about a specific product.
     *
     * @param productId Product identifier
     * @return Product
     */
    @GetMapping("/products/{productId}")
    ResponseEntity<Product> getProduct(@PathVariable("productId") String productId);

    /**
     * Create new product.
     * Add a new product to the catalog.
     *
     * @param body Product details
     * @return Product
     */
    @PostMapping("/products")
    ResponseEntity<Product> createProduct(@RequestBody ProductRequest body);
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
@EnableFeignClients(basePackages = "com.mycompany.api.client")
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
    product:
      url: https://api.example.com/api/v1
    order:
      url: https://api.example.com/api/v1
    customer:
      url: https://api.example.com/api/v1
```

4. **Inject and Use** in your services:
```java
@Service
public class ProductService {
    
    private final ProductClient productClient;
    
    public ProductService(ProductClient productClient) {
        this.productClient = productClient;
    }
    
    public Product getProduct(String productId) {
        ResponseEntity<Product> response = productClient.getProduct(productId);
        return response.getBody();
    }
    
    public Product createProduct(ProductRequest request) {
        ResponseEntity<Product> response = productClient.createProduct(request);
        return response.getBody();
    }
}
```

### Generated FeignConfiguration

When `generate_config: true`, a configuration class is created:

```java
package com.mycompany.api.client.config;

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
  ProductClient.java
  OrderClient.java
  CustomerClient.java
  PaymentClient.java
  InventoryClient.java
  config/
    FeignConfiguration.java
```
