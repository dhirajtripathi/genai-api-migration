import streamlit as st
from utils.agentic_helper import run_agentic_workflow
from utils.file_helper import create_zip_download
import os
import zipfile

def analyze_webmethods():
    flow_files = st.file_uploader("Upload webMethods flow files", type=["xml", "html"], accept_multiple_files=True, key="tab1_uploader")
    st.subheader("Analysis Preferences")
    granularity = st.selectbox("Microservices Granularity", options=["Coarse", "Fine", "Balanced"], index=2, key="tab1_granularity")
    focus_area = st.multiselect("Focus Areas", options=["Data Structures", "Business Logic", "Integrations"], default=["Data Structures", "Business Logic"], key="tab1_focus_area")

    if st.button("Analyze", key="tab1_analyze"):
        st.session_state.progress["tab1"] = "In Progress"
        if flow_files:
            flow_contents = [f"{file.name} ({'xml' if file.name.endswith('.xml') else 'html'}):\n{file.read().decode('utf-8')}" for file in flow_files]
            inputs = {
                "tab1": f"Files:\n{'---'.join(flow_contents)}\nPreferences: Granularity={granularity}, Focus Areas={', '.join(focus_area)}"
            }
            outputs = run_agentic_workflow(inputs, "tab1")
            
            files_dict = parse_ai_response_to_files(outputs.get("tab1", "No output generated"))
            st.session_state.progress["tab1"] = "Completed"
            st.markdown("### Generated Microservices Suggestions")
            for file_path, content in files_dict.items():
                st.subheader(file_path)
                st.markdown(content)
            create_project_zip(files_dict)
        else:
            st.warning("Please upload at least one flow file.")
    st.text(f"Progress: {st.session_state.progress['tab1']}")

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
    zip_path = f"{output_dir}/microservices_suggestion.zip"
    project_root = "suggestions"
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
        st.download_button(label="Download Microservices Suggestion ZIP", data=f, file_name="microservices_suggestion.zip", mime="application/zip")