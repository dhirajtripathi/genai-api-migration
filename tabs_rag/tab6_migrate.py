import streamlit as st
from utils.rai_helper import get_ai_response
from utils.file_helper import create_zip_download
import os
import zipfile

def migrate_data_logic():
    mapping_files = st.file_uploader("Upload webMethods flow files", type=["xml", "html"], accept_multiple_files=True, key="tab6_uploader")
    service_name = st.text_input("Target Microservice Name", value="SampleService", key="tab6_service_name")

    if st.button("Migrate", key="tab6_generate"):
        st.session_state.progress["tab6"] = "In Progress"
        if mapping_files:
            flow_contents = [f"{file.name}:\n{file.read().decode('utf-8')}" for file in mapping_files]
            prompt = (
                "Generate a migration plan and code for webMethods to Spring Boot using documentation context:\n"
                "- `migration.md`: Migration steps.\n"
                "- `src/main/java/com/example/{service_name}/migration/{ServiceName}Migration.java`: Migration code.\n"
                "Output each file prefixed with its path (e.g., `### migration.md`)."
            ).format(service_name=service_name.lower(), ServiceName=service_name) + "\nBased on these flows:\n" + "\n---\n".join(flow_contents)
            
            response = get_ai_response(prompt, use_rag=True)
            files_dict = parse_ai_response_to_files(response)
            
            st.session_state.progress["tab6"] = "Completed"
            st.markdown("### Generated Migration Files")
            for file_path, content in files_dict.items():
                st.subheader(file_path)
                if file_path.endswith(".md"):
                    st.markdown(content)
                else:
                    st.code(content, language="java")
            create_project_zip(service_name, files_dict)
        else:
            st.warning("Please upload at least one flow file.")
    st.text(f"Progress: {st.session_state.progress['tab6']}")

def parse_ai_response_to_files(response):
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
        st.download_button(label=f"Download {service_name} Migration Project ZIP", data=f, file_name=f"{service_name}_migration_project.zip", mime="application/zip")