import os
import shutil
import subprocess

def main():
    from config import JAVA_FOLDER, EXAMPLES_FOLDER, OPENAPI_FILE

    # Check if openapi.yaml exists
    if not os.path.exists(OPENAPI_FILE):
        print(f"❌ {OPENAPI_FILE} not found. Please ensure it exists in the workspace.")
        return

    # Delete java and examples folders if they exist
    for folder in [JAVA_FOLDER, EXAMPLES_FOLDER]:
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