import streamlit as st
from utils.rai_helper import get_ai_response
from utils.file_helper import create_zip_download
import os
import zipfile

def design_architecture():
    suggestion_file = st.file_uploader("Upload microservices suggestion (optional, e.g., from Tab 1)", type=["md", "txt"], key="tab2_uploader")
    st.subheader("Architecture Customization")
    num_services = st.number_input("Number of Microservices", min_value=1, value=3, key="tab2_num_services")
    comm_protocol = st.selectbox("Communication Protocol", options=["REST", "gRPC", "Message Queue"], index=0, key="tab2_comm_protocol")
    deploy_env = st.selectbox("Deployment Environment", options=["Azure Cloud", "AWS", "On-Premises"], index=0, key="tab2_deploy_env")

    if st.button("Generate Architecture", key="tab2_generate"):
        st.session_state.progress["tab2"] = "In Progress"
        prompt = (
            "Generate a Markdown document for a microservices architecture using Spring Boot and Boomi APIM, informed by webMethods documentation. Include:\n"
            "- Overview\n- Microservices Breakdown\n- Communication Patterns\n- Deployment Considerations\n- Boomi APIM Integration\n- Architecture Diagram (Mermaid)\n"
            "Output as `### architecture.md`.\n"
            f"Preferences: Number of Services={num_services}, Communication Protocol={comm_protocol}, Deployment Environment={deploy_env}"
        )
        if suggestion_file:
            suggestion_content = suggestion_file.read().decode("utf-8")
            prompt += f"\nBase it on these suggestions:\n{suggestion_content}"
        
        response = get_ai_response(prompt, use_rag=True)
        files_dict = parse_ai_response_to_files(response)
        
        st.session_state.progress["tab2"] = "Completed"
        st.markdown("### Generated Architecture")
        for file_path, content in files_dict.items():
            st.subheader(file_path)
            st.markdown(content)
        create_project_zip(files_dict)
    st.text(f"Progress: {st.session_state.progress['tab2']}")

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

def create_project_zip(files_dict):
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    zip_path = f"{output_dir}/architecture.zip"
    project_root = "architecture"
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
        st.download_button(label="Download Architecture ZIP", data=f, file_name="architecture.zip", mime="application/zip")