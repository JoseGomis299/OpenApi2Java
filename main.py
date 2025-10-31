import os
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
            subprocess.run(["rm", "-rf", folder])

    # Generate examples
    print("🚀 Generating examples...")
    subprocess.run(["python3", "generate_json_examples.py"], check=True)

    # Generate Java classes
    print("🚀 Generating Java classes...")
    subprocess.run(["python3", "generate_java_classes.py"], check=True)

    print("✅ Process complete!")

if __name__ == "__main__":
    main()
