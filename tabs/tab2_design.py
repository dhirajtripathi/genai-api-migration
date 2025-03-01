import streamlit as st
from utils.ai_helper import get_ai_response
from utils.file_helper import create_zip_download
import os
import zipfile

def design_architecture():
    # Upload artifacts (optional: microservices suggestion from Tab 1)
    suggestion_file = st.file_uploader(
        "Upload microservices suggestion (optional, e.g., from Tab 1)", 
        type=["md", "txt"], 
        key="tab2_uploader"
    )

    # Customization inputs
    st.subheader("Architecture Customization")
    num_services = st.number_input(
        "Number of Microservices", 
        min_value=1, 
        value=3, 
        key="tab2_num_services"
    )
    comm_protocol = st.selectbox(
        "Communication Protocol", 
        options=["REST", "gRPC", "Message Queue (e.g., Kafka, RabbitMQ)"], 
        index=0, 
        key="tab2_comm_protocol"
    )
    deploy_env = st.selectbox(
        "Deployment Environment", 
        options=["Azure Cloud", "AWS", "On-Premises"], 
        index=0, 
        key="tab2_deploy_env"
    )

    if st.button("Generate Architecture", key="tab2_generate"):
        st.session_state.progress["tab2"] = "In Progress"
        
        # Prepare the prompt
        base_prompt = (
            "Generate a detailed Markdown document for a microservices architecture using Spring Boot and Boomi APIM. Include the following sections:\n"
            "- **Overview**: Summary of the architecture.\n"
            "- **Microservices Breakdown**: List and describe each microservice (e.g., purpose, responsibilities).\n"
            "- **Communication Patterns**: Detail the protocol and interactions between services.\n"
            "- **Deployment Considerations**: Recommendations for the chosen environment (e.g., containerization, scaling).\n"
            "- **Boomi APIM Integration**: How Boomi manages API exposure and policies.\n"
            "- **Architecture Diagram**: A text-based diagram (use Mermaid syntax) showing service interactions.\n"
            "Provide the content in a single Markdown file prefixed with `### architecture.md`.\n"
            f"Design the architecture with {num_services} microservices, using {comm_protocol} for communication, and targeting {deploy_env} deployment."
        )
        
        # Incorporate Tab 1 suggestions if provided
        if suggestion_file:
            suggestion_content = suggestion_file.read().decode("utf-8")
            prompt = f"{base_prompt}\nBase the microservices breakdown on these suggestions:\n{suggestion_content}"
        else:
            prompt = base_prompt + "\nGenerate a generic architecture without specific microservice suggestions."

        # Get AI response
        response = get_ai_response(prompt)
        #RAG version
        # response = get_ai_response(prompt, use_rag=True)
        
        # Parse the response into files
        files_dict = parse_ai_response_to_files(response)
        
        # Display generated architecture
        st.session_state.progress["tab2"] = "Completed"
        st.markdown("### Generated Architecture")
        for file_path, content in files_dict.items():
            st.subheader(file_path)
            st.markdown(content)
        
        # Create ZIP with architecture file
        create_project_zip(files_dict)
    
    st.text(f"Progress: {st.session_state.progress['tab2']}")

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
    """Create a ZIP file with the architecture document."""
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
        st.download_button(
            label="Download Architecture ZIP",
            data=f,
            file_name="architecture.zip",
            mime="application/zip"
        )