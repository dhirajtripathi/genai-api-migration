import streamlit as st
from utils.rai_helper import get_ai_response
from utils.file_helper import create_zip_download
import os
import zipfile
from io import BytesIO

def boomi_apim_integration():
    zip_file = st.file_uploader("Upload Tab 3 Microservice ZIP", type=["zip"], key="tab4_uploader")
    service_name = st.text_input("Microservice Name", value="SampleService", key="tab4_service_name")
    st.subheader("Boomi APIM Policy Customization")
    rate_limit = st.number_input("Rate Limit (requests per minute)", min_value=1, value=100, key="tab4_rate_limit")
    auth_type = st.selectbox("Authentication Type", options=["None", "OAuth2", "API Key", "Basic"], index=1, key="tab4_auth_type")

    if st.button("Generate OpenAPI", key="tab4_generate"):
        st.session_state.progress["tab4"] = "In Progress"
        prompt = (
            "Generate an OpenAPI 3.0 YAML file and Boomi APIM instructions using webMethods documentation context:\n"
            "- `openapi.yaml`: OpenAPI spec with 2 endpoints and Boomi policies (x-boomi-*).\n"
            "- `README.md`: Import instructions.\n"
            "Output each file prefixed with its path (e.g., `### openapi.yaml`).\n"
            f"Policies: Rate Limit={rate_limit} req/min, Authentication={auth_type}"
        )
        if zip_file:
            contents = extract_zip_contents(zip_file)
            if contents:
                prompt += "\nBased on this microservice code:\n" + "\n".join([f"{k}:\n{v}" for k, v in contents.items()])
        
        response = get_ai_response(prompt, use_rag=True)
        files_dict = parse_ai_response_to_files(response)
        
        st.session_state.progress["tab4"] = "Completed"
        st.markdown("### Generated Boomi APIM Integration Files")
        for file_path, content in files_dict.items():
            st.subheader(file_path)
            if file_path.endswith(".yaml"):
                st.code(content, language="yaml")
            else:
                st.markdown(content)
        create_project_zip(service_name, files_dict)
    st.text(f"Progress: {st.session_state.progress['tab4']}")

def extract_zip_contents(zip_file):
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
    zip_path = f"{output_dir}/{service_name}_boomi_integration.zip"
    project_root = f"{service_name}-boomi-integration"
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
        st.download_button(label=f"Download {service_name} Boomi Integration ZIP", data=f, file_name=f"{service_name}_boomi_integration.zip", mime="application/zip")