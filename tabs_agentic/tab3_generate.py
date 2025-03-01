import streamlit as st
from utils.agentic_helper import run_agentic_workflow
from utils.file_helper import create_zip_download
import os
import zipfile

def generate_microservices():
    # Upload artifacts (e.g., architecture Markdown from Tab 2)
    arch_file = st.file_uploader(
        "Upload architecture Markdown (e.g., from Tab 2)", 
        type=["md"], 
        key="tab3_uploader"
    )

    # User input for microservice name
    service_name = st.text_input(
        "Microservice Name (e.g., OrderService)", 
        value="SampleService", 
        key="tab3_service_name"
    )

    if st.button("Generate Microservices", key="tab3_generate"):
        st.session_state.progress["tab3"] = "In Progress"
        
        # Prepare input data
        input_data = f"Microservice Name: {service_name}"
        if arch_file:
            arch_content = arch_file.read().decode("utf-8")
            input_data += f"\nTab 2 Architecture:\n{arch_content}"
        
        inputs = {
            "tab1": "",  # Empty for prior tabs
            "tab2": "",
            "tab3": input_data
        }
        
        # Run the agentic workflow
        outputs = run_agentic_workflow(inputs, "tab3")
        
        # Parse and display response
        files_dict = parse_ai_response_to_files(outputs.get("tab3", "No output generated"))
        
        st.session_state.progress["tab3"] = "Completed"
        st.markdown("### Generated Microservice Files")
        for file_path, content in files_dict.items():
            st.subheader(file_path)
            st.code(content, language="java" if file_path.endswith(".java") else "xml" if file_path.endswith(".xml") else "yaml")
        
        # Create ZIP with project structure
        create_project_zip(service_name, files_dict)
    
    st.text(f"Progress: {st.session_state.progress['tab3']}")

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
    """Create a ZIP file with a Maven project structure."""
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    zip_path = f"{output_dir}/{service_name}_project.zip"
    project_root = f"{service_name}-microservice"
    
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
            label=f"Download {service_name} Project ZIP",
            data=f,
            file_name=f"{service_name}_project.zip",
            mime="application/zip"
        )

# Ensure this runs only when imported as a module
if __name__ == "__main__":
    generate_microservices()