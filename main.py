import os
import shutil
import subprocess

def main():
    from config import get_config, get_openapi_definition_files

    config = get_config()

    JAVA_FOLDER = config['java']['java_folder']
    EXAMPLES_FOLDER = config['json']['examples_folder']
    FEIGN_FOLDER = config['feign']['feign_folder']

    # Get definition files
    definition_files = get_openapi_definition_files()

    if not definition_files:
        print("❌ No OpenAPI definition files found!")
        print("   Please add OpenAPI YAML files to the openApiDefinitions directory.")
        return

    print(f"\n{'='*70}")
    print(f"  OpenAPI to Java Generator")
    print(f"{'='*70}")
    print(f"  Definitions to process: {len(definition_files)}")
    print(f"{'='*70}\n")

    # Delete output folders if they exist
    for folder in [JAVA_FOLDER, EXAMPLES_FOLDER, FEIGN_FOLDER]:
        if os.path.exists(folder):
            print(f"🗑️  Deleting folder: {folder}")
            shutil.rmtree(folder)

    # Generate examples (optional, for reference)
    print(f"\n{'='*70}")
    print("🚀 Step 1: Generating JSON examples...")
    print(f"{'='*70}")
    result = subprocess.run(["python3", "generate_json_examples.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ Error generating JSON examples:")
        print(result.stderr)
        return

    # Generate Java classes directly from OpenAPI schema
    print(f"\n{'='*70}")
    print("🚀 Step 2: Generating Java classes from OpenAPI schema...")
    print(f"{'='*70}")
    result = subprocess.run(["python3", "generate_java_classes.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ Error generating Java classes:")
        print(result.stderr)
        return

    # Generate Feign clients
    print(f"\n{'='*70}")
    print("🚀 Step 3: Generating Feign clients from OpenAPI specification...")
    print(f"{'='*70}")
    result = subprocess.run(["python3", "generate_feign_clients.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ Error generating Feign clients:")
        print(result.stderr)
        return

    print(f"\n{'='*70}")
    print("✅ Process complete!")
    print(f"{'='*70}")
    print(f"  📁 Examples: {EXAMPLES_FOLDER}")
    print(f"  📁 Java Classes: {JAVA_FOLDER}")
    print(f"  📁 Feign Clients: {FEIGN_FOLDER}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()