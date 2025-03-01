import streamlit as st
from utils.ai_helper import get_ai_response
from utils.file_helper import create_zip_download
import os
import zipfile

def migrate_data_logic():
    # Upload artifacts (e.g., webMethods mappings, XML files)
    mapping_files = st.file_uploader(
        "Upload webMethods mappings or XML files", 
        type=["xml", "txt"], 
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
        
        # Prepare the prompt
        base_prompt = (
            "Generate a detailed migration plan to transform webMethods data and logic into a Spring Boot microservice. Provide the output as a set of files:\n"
            "- `migration.md`: A Markdown file with step-by-step instructions for migrating data and logic.\n"
            "- `src/main/java/com/example/{service_name}/migration/{ServiceName}Migration.java`: A Java class with code snippets for data migration and logic conversion.\n"
            "Replace `{service_name}` with the provided microservice name in lowercase and `{ServiceName}` with its CamelCase version.\n"
            "Include:\n"
            "- Steps to extract data from webMethods (e.g., database queries, XML parsing).\n"
            "- Mapping logic to transform webMethods data into microservice entities.\n"
            "- Conversion of business logic into service methods.\n"
            "Provide the content of each file as a separate section in the response, prefixed with the file path (e.g., `### migration.md`)."
        )
        
        # Incorporate uploaded artifacts if provided
        if mapping_files:
            mapping_contents = [file.read().decode("utf-8") for file in mapping_files]
            prompt = (
                f"{base_prompt}\nAnalyze these webMethods artifacts and tailor the migration plan accordingly:\n"
                + "\n---\n".join(mapping_contents)
            )
        else:
            prompt = base_prompt + "\nGenerate a generic migration plan for a typical webMethods integration."
        
        # Add service name to prompt
        prompt += f"\nMicroservice Name: {service_name}"

        # Get AI response
        response = get_ai_response(prompt)

        #RAG version
        # response = get_ai_response(prompt, use_rag=True)        
        
        # Parse the response into files
        files_dict = parse_ai_response_to_files(response, service_name)
        
        # Display generated migration content
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
    """Create a ZIP file with a Maven project structure for migration."""
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    zip_path = f"{output_dir}/{service_name}_migration_project.zip"
    project_root = f"{service_name}-migration-project"
    
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
            label=f"Download {service_name} Migration Project ZIP",
            data=f,
            file_name=f"{service_name}_migration_project.zip",
            mime="application/zip"
        )