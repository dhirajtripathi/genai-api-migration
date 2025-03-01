import streamlit as st
from utils.agentic_helper import run_agentic_workflow
from utils.file_helper import create_zip_download
import os
import zipfile

def migrate_data_logic():
    # Upload webMethods flow files
    mapping_files = st.file_uploader(
        "Upload webMethods flow files (e.g., flow.xml or flow.html)", 
        type=["xml", "html"], 
        accept_multiple_files=True, 
        key="tab6_uploader"
    )

    # User input for target microservice name
    service_name = st.text_input(
        "Target Microservice Name (e.g., OrderService, must match previous tabs)", 
        value="SampleService", 
        key="tab6_service_name"
    )

    if st.button("Migrate", key="tab6_generate"):
        st.session_state.progress["tab6"] = "In Progress"
        
        # Prepare input data
        if mapping_files:
            flow_contents = [f"{file.name} ({'xml' if file.name.endswith('.xml') else 'html'}):\n{file.read().decode('utf-8')}" for file in mapping_files]
            input_data = f"Microservice Name: {service_name}\nFlow Files:\n{'---'.join(flow_contents)}"
        else:
            st.warning("Please upload at least one flow file.")
            st.session_state.progress["tab6"] = "Not Started"
            return
        
        inputs = {
            "tab1": "",
            "tab2": "",
            "tab3": "",
            "tab4": "",
            "tab5": "",
            "tab6": input_data
        }
        
        # Run the agentic workflow
        outputs = run_agentic_workflow(inputs, "tab6")
        
        # Parse and display response
        files_dict = parse_ai_response_to_files(outputs.get("tab6", "No output generated"))
        
        st.session_state.progress["tab6"] = "Completed"
        st.markdown("### Generated Migration Files")
        for file_path, content in files_dict.items():
            st.subheader(file_path)
            if file_path.endswith(".md"):
                st.markdown(content)
            else:
                st.code(content, language="java")
        
        # Create ZIP with project structure
        create_project_zip(service_name, files_dict)
    
    st.text(f"Progress: {st.session_state.progress['tab6']}")

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
    """Create a ZIP file with a Maven project structure for migration."""
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    zip_path = f"{output_dir}/{service_name}_migration_project.zip"
    project_root = f"{service_name}-migration-project"
    
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
            label=f"Download {service_name} Migration Project ZIP",
            data=f,
            file_name=f"{service_name}_migration_project.zip",
            mime="application/zip"
        )

# Ensure this runs only when imported as a module
if __name__ == "__main__":
    migrate_data_logic()