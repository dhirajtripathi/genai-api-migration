import streamlit as st
from utils.rai_helper import get_ai_response
from utils.file_helper import create_zip_download
import os
import zipfile
from bs4 import BeautifulSoup

def analyze_webmethods():
    flow_files = st.file_uploader("Upload webMethods flow files (e.g., flow.xml or flow.html)", type=["xml", "html"], accept_multiple_files=True, key="tab1_uploader")
    st.subheader("Analysis Preferences")
    granularity = st.selectbox("Microservices Granularity", options=["Coarse", "Fine", "Balanced"], index=2, key="tab1_granularity")
    focus_area = st.multiselect("Focus Areas", options=["Data Structures", "Business Logic", "Integrations"], default=["Data Structures", "Business Logic"], key="tab1_focus_area")

    if st.button("Analyze", key="tab1_analyze"):
        st.session_state.progress["tab1"] = "In Progress"
        if flow_files:
            flow_contents = []
            for flow_file in flow_files:
                content = flow_file.read().decode("utf-8")
                file_type = "xml" if flow_file.name.endswith(".xml") else "html"
                soup = BeautifulSoup(content, "html.parser") if file_type == "html" else None
                if file_type == "html" and not (soup.find("table") or soup.find(class_="flowStep")):
                    st.warning(f"{flow_file.name} does not appear to contain webMethods flow data.")
                    continue
                flow_contents.append(f"{file_type.upper()} Content:\n{content}")
            
            if not flow_contents:
                st.warning("No valid flow files to analyze.")
                st.session_state.progress["tab1"] = "Failed"
                return
            
            prompt = (
                "Analyze the provided webMethods flow files (XML or HTML) and suggest a microservices architecture using webMethods documentation context. Generate a Markdown file with:\n"
                "- Summary\n- Suggested Microservices (Name, Responsibilities, Endpoints, Data Entities)\n- Dependencies\n- Insights\n- Diagram (Mermaid syntax)\n"
                "Output as `### microservices_suggestion.md`.\n"
                f"Preferences: Granularity={granularity}, Focus Areas={', '.join(focus_area)}"
            ) + "\nAnalyze these flow files:\n" + "\n---\n".join(flow_contents)
            
            response = get_ai_response(prompt, use_rag=True)
            files_dict = parse_ai_response_to_files(response)
            
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