import streamlit as st
from utils.agentic_helper import run_agentic_workflow
from utils.file_helper import create_zip_download
import os
import zipfile
from io import BytesIO

def generate_howto():
    # Upload previous outputs (e.g., from Tabs 1-6)
    previous_outputs = st.file_uploader(
        "Upload previous outputs (e.g., ZIPs or files from Tabs 1-6)", 
        type=["zip", "md", "java", "yaml", "txt"], 
        accept_multiple_files=True, 
        key="tab7_uploader"
    )

    if st.button("Generate HowTo", key="tab7_generate"):
        st.session_state.progress["tab7"] = "In Progress"
        
        # Prepare input data
        input_data = "Generate a HowTo guide based on available inputs."
        if previous_outputs:
            contents = []
            for output_file in previous_outputs:
                if output_file.name.endswith(".zip"):
                    zip_contents = extract_zip_contents(output_file)
                    contents.extend([f"{filename}:\n{content}" for filename, content in zip_contents.items()])
                else:
                    content = output_file.read().decode("utf-8")
                    contents.append(f"{output_file.name}:\n{content}")
            input_data += "\nPrevious Outputs:\n" + "\n---\n".join(contents)
        else:
            input_data += "\nNo previous outputs provided; generate a generic guide."
        
        inputs = {
            "tab1": "",
            "tab2": "",
            "tab3": "",
            "tab4": "",
            "tab5": "",
            "tab6": "",
            "tab7": input_data
        }
        
        # Run the agentic workflow
        outputs = run_agentic_workflow(inputs, "tab7")
        
        # Parse and display response
        files_dict = parse_ai_response_to_files(outputs.get("tab7", "No output generated"))
        
        st.session_state.progress["tab7"] = "Completed"
        st.markdown("### Generated HowTo Instructions")
        for file_path, content in files_dict.items():
            st.subheader(file_path)
            st.markdown(content)
        
        # Create ZIP with project structure
        create_project_zip(files_dict)
    
    st.text(f"Progress: {st.session_state.progress['tab7']}")

def extract_zip_contents(zip_file):
    """Extract contents from the uploaded ZIP file."""
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
    """Parse the agent's response into a dictionary of file paths and contents."""
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
    """Create a ZIP file with the HowTo instructions."""
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
        st.download_button(
            label="Download HowTo ZIP",
            data=f,
            file_name="howto.zip",
            mime="application/zip"
        )

# Ensure this runs only when imported as a module
if __name__ == "__main__":
    generate_howto()