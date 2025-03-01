import streamlit as st
from utils.ai_helper import get_ai_response
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
        
        # Prepare the prompt
        base_prompt = (
            "Generate a complete Spring Boot microservice project as a set of files with the following structure:\n"
            "- `pom.xml`: Maven configuration with Spring Boot dependencies.\n"
            "- `src/main/java/com/example/{service_name}/controller/{ServiceName}Controller.java`: REST controller with at least 2 endpoints (GET, POST).\n"
            "- `src/main/java/com/example/{service_name}/service/{ServiceName}Service.java`: Service layer with business logic.\n"
            "- `src/main/java/com/example/{service_name}/entity/{ServiceName}Entity.java`: Entity class with JPA annotations.\n"
            "- `src/main/resources/application.yml`: Configuration file with basic settings (e.g., port, datasource).\n"
            "Replace `{service_name}` with the provided microservice name in lowercase and `{ServiceName}` with its CamelCase version.\n"
            "Provide the content of each file as a separate section in the response, prefixed with the file path (e.g., `### pom.xml`)."
        )
        
        # Incorporate architecture if provided
        if arch_file:
            arch_content = arch_file.read().decode("utf-8")
            prompt = f"{base_prompt}\nBase the microservice on this architecture:\n{arch_content}"
        else:
            prompt = base_prompt
        
        # Add microservice name to prompt
        prompt += f"\nMicroservice Name: {service_name}"

        # Get AI response
        response = get_ai_response(prompt)

        #RAG version
        # response = get_ai_response(prompt, use_rag=True)        
        
        # Parse the response into files
        files_dict = parse_ai_response_to_files(response, service_name)
        
        # Display generated code
        st.session_state.progress["tab3"] = "Completed"
        st.markdown("### Generated Microservice Files")
        for file_path, content in files_dict.items():
            st.subheader(file_path)
            st.code(content, language="java" if file_path.endswith(".java") else "xml" if file_path.endswith(".xml") else "yaml")
        
        # Create ZIP with project structure
        create_project_zip(service_name, files_dict)
    
    st.text(f"Progress: {st.session_state.progress['tab3']}")

def parse_ai_response_to_files(response, service_name):
    """Parse the AI response into a dictionary of file paths and contents."""
    files_dict = {}
    current_file = None
    current_content = []
    
    for line in response.splitlines():
        if line.startswith("### "):
            if current_file and current_content:
                files_dict[current_file] = "\n".join(current_content).strip()
            current_file = line[4:].strip()  # Remove "### "
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
            # Adjust file path to match Maven structure
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