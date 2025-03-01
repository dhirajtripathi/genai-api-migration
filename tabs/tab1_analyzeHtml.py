import streamlit as st
from utils.ai_helper import get_ai_response
from utils.file_helper import create_zip_download
import os
import zipfile
from bs4 import BeautifulSoup

def analyze_webmethods():
    # Upload webMethods flow files (HTML or XML)
    flow_files = st.file_uploader(
        "Upload webMethods flow files (e.g., flow.xml or flow.html)", 
        type=["xml", "html"], 
        accept_multiple_files=True, 
        key="tab1_uploader"
    )

    # Customization inputs
    st.subheader("Analysis Preferences")
    granularity = st.selectbox(
        "Microservices Granularity", 
        options=["Coarse (fewer, larger services)", "Fine (more, smaller services)", "Balanced"], 
        index=2, 
        key="tab1_granularity"
    )
    focus_area = st.multiselect(
        "Focus Areas", 
        options=["Data Structures", "Business Logic", "Integrations"], 
        default=["Data Structures", "Business Logic"], 
        key="tab1_focus_area"
    )

    if st.button("Analyze", key="tab1_analyze"):
        st.session_state.progress["tab1"] = "In Progress"
        
        if flow_files:
            # Process and validate uploaded files
            flow_contents = []
            for flow_file in flow_files:
                try:
                    content = flow_file.read().decode("utf-8")
                    if flow_file.name.endswith(".xml"):
                        # Validate XML
                        import xml.etree.ElementTree as ET
                        ET.fromstring(content)
                        flow_contents.append(("xml", content))
                    elif flow_file.name.endswith(".html"):
                        # Validate and parse HTML
                        soup = BeautifulSoup(content, "html.parser")
                        # Basic check for webMethods flow content (e.g., tables or specific classes)
                        if not soup.find("table") and not soup.find(class_="flowStep"):
                            st.warning(f"{flow_file.name} does not appear to contain webMethods flow data.")
                            continue
                        flow_contents.append(("html", str(soup)))
                    else:
                        st.warning(f"Unsupported file type: {flow_file.name}")
                        continue
                except Exception as e:
                    st.error(f"Error processing {flow_file.name}: {e}")
                    st.session_state.progress["tab1"] = "Failed"
                    return
            
            if not flow_contents:
                st.warning("No valid flow files to analyze.")
                st.session_state.progress["tab1"] = "Failed"
                return
            
            # Prepare the prompt
            base_prompt = (
                "Analyze the provided webMethods flow files (in XML or HTML format) and suggest a microservices architecture. Generate a detailed Markdown file with the following sections:\n"
                "- **Summary**: Overview of the analysis and key findings (e.g., complexity, dependencies).\n"
                "- **Suggested Microservices**: List each microservice with:\n"
                "  - Name\n"
                "  - Responsibilities\n"
                "  - Potential Endpoints (e.g., GET /resource, POST /resource)\n"
                "  - Data Entities (e.g., key fields or objects)\n"
                "- **Dependencies**: Detail dependencies between suggested microservices (e.g., calls, data sharing).\n"
                "- **Insights**: Observations about the flows (e.g., integration points, logic complexity).\n"
                "- **Diagram**: A Mermaid syntax diagram showing suggested microservices and their dependencies.\n"
                "Provide the content in a single Markdown file prefixed with `### microservices_suggestion.md`.\n"
                f"Apply the following preferences:\n"
                f"- Granularity: {granularity}\n"
                f"- Focus Areas: {', '.join(focus_area)}\n"
                "For HTML files, interpret the flow steps, mappings, and integrations from the structured content (e.g., tables, divs with class 'flowStep')."
            )
            
            # Combine contents with type indicators
            prompt_parts = []
            for file_type, content in flow_contents:
                prompt_parts.append(f"{file_type.upper()} Content:\n{content}")
            prompt = f"{base_prompt}\nAnalyze these flow files:\n" + "\n---\n".join(prompt_parts)
            
            # Get AI response
            response = get_ai_response(prompt)
            
            # Parse the response into files
            files_dict = parse_ai_response_to_files(response)
            
            # Display generated suggestions
            st.session_state.progress["tab1"] = "Completed"
            st.markdown("### Generated Microservices Suggestions")
            for file_path, content in files_dict.items():
                st.subheader(file_path)
                st.markdown(content)
            
            # Create ZIP with suggestions
            create_project_zip(files_dict)
        else:
            st.warning("Please upload at least one flow file.")
    
    st.text(f"Progress: {st.session_state.progress['tab1']}")

def parse_ai_response_to_files(response):
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

def create_project_zip(files_dict):
    """Create a ZIP file with the microservices suggestions."""
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
        st.download_button(
            label="Download Microservices Suggestion ZIP",
            data=f,
            file_name="microservices_suggestion.zip",
            mime="application/zip"
        )