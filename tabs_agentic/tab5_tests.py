import streamlit as st
from utils.agentic_helper import run_agentic_workflow
from utils.file_helper import create_zip_download
import os
import zipfile
from io import BytesIO

def generate_unit_tests():
    # Upload Tab 3 ZIP file
    code_file = st.file_uploader(
        "Upload Tab 3 Microservice ZIP (e.g., OrderService_project.zip)", 
        type=["zip"], 
        key="tab5_uploader"
    )

    # User input for service name
    service_name = st.text_input(
        "Service Name (e.g., OrderService, must match Tab 3)", 
        value="SampleService", 
        key="tab5_service_name"
    )

    if st.button("Generate Tests", key="tab5_generate"):
        st.session_state.progress["tab5"] = "In Progress"
        
        # Prepare input data
        input_data = f"Service Name: {service_name}"
        if code_file:
            contents = extract_zip_contents(code_file)
            if contents:
                input_data += "\nTab 3 Microservice Contents:\n" + "\n".join([f"{filename}:\n{content}" for filename, content in contents.items()])
            else:
                st.warning("No valid files found in ZIP.")
        
        inputs = {
            "tab1": "",
            "tab2": "",
            "tab3": "",
            "tab4": "",
            "tab5": input_data
        }
        
        # Run the agentic workflow
        outputs = run_agentic_workflow(inputs, "tab5")
        
        # Parse and display response
        files_dict = parse_ai_response_to_files(outputs.get("tab5", "No output generated"))
        
        st.session_state.progress["tab5"] = "Completed"
        st.markdown("### Generated Unit Test Files")
        for file_path, content in files_dict.items():
            st.subheader(file_path)
            st.code(content, language="java" if file_path.endswith(".java") else "xml")
        
        # Create ZIP with project structure
        create_project_zip(service_name, files_dict)
    
    st.text(f"Progress: {st.session_state.progress['tab5']}")

def extract_zip_contents(zip_file):
    """Extract contents from the uploaded ZIP file."""
    contents = {}
    try:
        with zipfile.ZipFile(BytesIO(zip_file.read()), "r") as zip_ref:
            for file_info in zip_ref.infolist():
                if not file_info.is_dir() and file_info.filename.endswith((".java", ".yml", ".yaml", ".xml")):
                    with zip_ref.open(file_info) as f:
                        contents[file_info.filename] = f.read().decode("utf-8")
    except Exception as e:
        st.warning(f"Failed to extract ZIP contents: {e}")
    return contents

def parse_ai_response_to_files(response):
    """Parse the agent's response into a dictionary of file paths and contents."""
    files_dict = {}
    current_file = None
    current_content = []
    
    for line in response.splitlines():
        if line.startswith("### "):
            if current_file and current_content:
                files_dict[current_file] = "\n".join(current_content).strip()
            current_file = line[4:].strip()
            current_content = []
        elif current_file:
            current_content.append(line)
    
    if current_file and current_content:
        files_dict[current_file] = "\n".join(current_content).strip()
    
    return files_dict

def create_project_zip(service_name, files_dict):
    """Create a ZIP file with a Maven project structure for tests."""
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    zip_path = f"{output_dir}/{service_name}_test_project.zip"
    project_root = f"{service_name}-test-project"
    
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path, content in files_dict.items():
            full_path = os.path.join(project_root, file_path)
            temp_path = os.path.join(output_dir, full_path)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, "w") as f:
                f.write(content)
            zipf.write(temp_path, full_path)
            os.remove(temp_path)
    
    with open(zip_path, "rb") as f:
        st.download_button(
            label=f"Download {service_name} Test Project ZIP",
            data=f,
            file_name=f"{service_name}_test_project.zip",
            mime="application/zip"
        )

# Ensure this runs only when imported as a module
if __name__ == "__main__":
    generate_unit_tests()