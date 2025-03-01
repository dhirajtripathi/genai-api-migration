import streamlit as st
from utils.rai_helper import get_ai_response
from utils.file_helper import create_zip_download
import os
import zipfile
from io import BytesIO

def generate_howto():
    previous_outputs = st.file_uploader("Upload previous outputs (e.g., from Tabs 1-6)", type=["zip", "md", "java", "yaml", "txt"], accept_multiple_files=True, key="tab7_uploader")

    if st.button("Generate HowTo", key="tab7_generate"):
        st.session_state.progress["tab7"] = "In Progress"
        prompt = (
            "Generate a HowTo guide for transforming webMethods to microservices using documentation context:\n"
            "- Introduction\n- Step-by-Step Instructions\n- Best Practices\n"
            "Output as `### howto.md`."
        )
        if previous_outputs:
            contents = []
            for output_file in previous_outputs:
                if output_file.name.endswith(".zip"):
                    zip_contents = extract_zip_contents(output_file)
                    contents.extend([f"{k}:\n{v}" for k, v in zip_contents.items()])
                else:
                    contents.append(f"{output_file.name}:\n{output_file.read().decode('utf-8')}")
            prompt += "\nBased on these outputs:\n" + "\n---\n".join(contents)
        
        response = get_ai_response(prompt, use_rag=True)
        files_dict = parse_ai_response_to_files(response)
        
        st.session_state.progress["tab7"] = "Completed"
        st.markdown("### Generated HowTo Instructions")
        for file_path, content in files_dict.items():
            st.subheader(file_path)
            st.markdown(content)
        create_project_zip(files_dict)
    st.text(f"Progress: {st.session_state.progress['tab7']}")

def extract_zip_contents(zip_file):
    contents = {}
    try:
        with zipfile.ZipFile(BytesIO(zip_file.read()), "r") as zip_ref:
            for file_info in zip_ref.infolist():
                if not file_info.is_dir():
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

def create_project_zip(files_dict):
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    zip_path = f"{output_dir}/howto.zip"
    project_root = "howto"
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
        st.download_button(label="Download HowTo ZIP", data=f, file_name="howto.zip", mime="application/zip")