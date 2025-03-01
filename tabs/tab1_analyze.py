import streamlit as st
from utils.ai_helper import get_ai_response
from utils.file_helper import create_zip_download
import os
import zipfile
import xml.etree.ElementTree as ET

def analyze_webmethods():
    # Upload webMethods XML files
    xml_files = st.file_uploader(
        "Upload webMethods XML files (e.g., flow.xml)", 
        type=["xml"], 
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
        
        if xml_files:
            # Validate XML files
            xml_contents = []
            for xml_file in xml_files:
                try:
                    xml_content = xml_file.read().decode("utf-8")
                    # Check XML validity
                    ET.fromstring(xml_content)  # Raises exception if invalid
                    xml_contents.append(xml_content)
                except ET.ParseError as e:
                    st.error(f"Invalid XML in {xml_file.name}: {e}")
                    st.session_state.progress["tab1"] = "Failed"
                    return
                except Exception as e:
                    st.error(f"Error processing {xml_file.name}: {e}")
                    st.session_state.progress["tab1"] = "Failed"
                    return
            
            if not xml_contents:
                st.warning("No valid XML files to analyze.")
                st.session_state.progress["tab1"] = "Failed"
                return
            
            # Prepare the prompt
            base_prompt = (
                "Analyze the provided webMethods XML files and suggest a microservices architecture. Generate a detailed Markdown file with the following sections:\n"
                "- **Summary**: Overview of the analysis and key findings (e.g., complexity, dependencies).\n"
                "- **Suggested Microservices**: List each microservice with:\n"
                "  - Name\n"
                "  - Responsibilities\n"
                "  - Potential Endpoints (e.g., GET /resource, POST /resource)\n"
                "  - Data Entities (e.g., key fields or objects)\n"
                "- **Dependencies**: Detail dependencies between suggested microservices (e.g., calls, data sharing).\n"
                "- **Insights**: Observations about the XML (e.g., integration points, logic complexity).\n"
                "- **Diagram**: A Mermaid syntax diagram showing suggested microservices and their dependencies.\n"
                "Provide the content in a single Markdown file prefixed with `### microservices_suggestion.md`.\n"
                f"Apply the following preferences:\n"
                f"- Granularity: {granularity}\n"
                f"- Focus Areas: {', '.join(focus_area)}\n"
            )
            
            prompt = f"{base_prompt}\nAnalyze these XML files:\n" + "\n---\n".join(xml_contents)
            
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
            st.warning("Please upload at least one XML file.")
    
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