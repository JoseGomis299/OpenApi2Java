import os
import shutil
import subprocess

# Paths to folders and files
java_folder = "java"
examples_folder = "examples"
openapi_file = "openapi.yaml"

def main():
    # Check if openapi.yaml exists
    if not os.path.exists(openapi_file):
        print(f"❌ {openapi_file} not found. Please ensure it exists in the workspace.")
        return

    # Delete java and examples folders if they exist
    for folder in [java_folder, examples_folder]:
        if os.path.exists(folder):
            print(f"🗑️ Deleting folder: {folder}")
            shutil.rmtree(folder)

    # Generate examples (optional, for reference)
    print("🚀 Generating JSON examples...")
    subprocess.run(["python3", "generate_json_examples.py"], check=True)

    # Generate Java classes directly from OpenAPI schema
    print("🚀 Generating Java classes from OpenAPI schema...")
    subprocess.run(["python3", "generate_java_classes.py"], check=True)

    print("✅ Process complete!")

if __name__ == "__main__":
    main()