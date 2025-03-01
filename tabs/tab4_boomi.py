import streamlit as st
from utils.ai_helper import get_ai_response
from utils.file_helper import create_zip_download
import os
import zipfile
import yaml
from io import BytesIO

def boomi_apim_integration():
    # Upload Tab 3 ZIP file
    zip_file = st.file_uploader(
        "Upload Tab 3 Microservice ZIP (e.g., OrderService_project.zip)", 
        type=["zip"], 
        key="tab4_uploader"
    )

    # User input for microservice name
    service_name = st.text_input(
        "Microservice Name (e.g., OrderService, must match Tab 3)", 
        value="SampleService", 
        key="tab4_service_name"
    )

    # Policy customization inputs
    st.subheader("Boomi APIM Policy Customization")
    rate_limit = st.number_input(
        "Rate Limit (requests per minute)", 
        min_value=1, 
        value=100, 
        key="tab4_rate_limit"
    )
    auth_type = st.selectbox(
        "Authentication Type", 
        options=["None", "OAuth2", "API Key", "Basic"], 
        index=1, 
        key="tab4_auth_type"
    )

    if st.button("Generate OpenAPI", key="tab4_generate"):
        st.session_state.progress["tab4"] = "In Progress"
        
        # Prepare the prompt
        base_prompt = (
            "Generate a detailed OpenAPI 3.0 YAML file for a Spring Boot microservice integrated with Boomi APIM policies. Provide the output as a set of files:\n"
            "- `openapi.yaml`: OpenAPI 3.0 specification with at least 2 endpoints (GET, POST), including request/response schemas and Boomi-specific policies as vendor extensions (x-boomi-*).\n"
            "- `README.md`: Instructions for importing and deploying the OpenAPI spec into Boomi APIM.\n"
            "Use the microservice name provided to define paths (e.g., /{service_name}/...) and components.\n"
            "Incorporate the specified policies:\n"
            f"- Rate Limit: {rate_limit} requests per minute\n"
            f"- Authentication: {auth_type}\n"
            "Provide the content of each file as a separate section in the response, prefixed with the file path (e.g., `### openapi.yaml`)."
        )
        
        # Extract and incorporate Tab 3 ZIP contents if provided
        if zip_file:
            code_contents = extract_zip_contents(zip_file)
            if code_contents:
                prompt = (
                    f"{base_prompt}\nTailor the OpenAPI spec based on these microservice files from Tab 3:\n"
                    + "\n---\n".join([f"{filename}:\n{content}" for filename, content in code_contents.items()])
                )
            else:
                prompt = base_prompt + "\nNo valid files found in ZIP; generate a generic OpenAPI spec."
        else:
            prompt = base_prompt + "\nGenerate a generic OpenAPI spec for a typical Spring Boot microservice."
        
        # Add service name to prompt
        prompt += f"\nMicroservice Name: {service_name}"

        # Get AI response
        response = get_ai_response(prompt)

        #RAG version
        # response = get_ai_response(prompt, use_rag=True)        
        
        # Parse the response into files
        files_dict = parse_ai_response_to_files(response, service_name)
        
        # Validate OpenAPI YAML
        if "openapi.yaml" in files_dict:
            is_valid, validation_error = validate_openapi_yaml(files_dict["openapi.yaml"])
            if not is_valid:
                st.error(f"Generated OpenAPI YAML is invalid: {validation_error}")
                files_dict["openapi.yaml"] += "\n# Note: Validation failed; review and correct the YAML manually."
        
        # Display generated content
        st.session_state.progress["tab4"] = "Completed"
        st.markdown("### Generated Boomi APIM Integration Files")
        for file_path, content in files_dict.items():
            st.subheader(file_path)
            if file_path.endswith(".yaml"):
                st.code(content, language="yaml")
            else:
                st.markdown(content)
        
        # Create ZIP with project structure
        create_project_zip(service_name, files_dict)
    
    st.text(f"Progress: {st.session_state.progress['tab4']}")

def parse_ai_response_to_files(response, service_name):
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

def extract_zip_contents(zip_file):
    """Extract contents from the uploaded ZIP file."""
    contents = {}
    try:
        with zipfile.ZipFile(BytesIO(zip_file.read()), "r") as zip_ref:
            for file_info in zip_ref.infolist():
                if not file_info.is_dir() and file_info.filename.endswith((".java", ".yml", ".yaml", ".properties")):
                    with zip_ref.open(file_info) as f:
                        contents[file_info.filename] = f.read().decode("utf-8")
    except Exception as e:
        st.warning(f"Failed to extract ZIP contents: {e}")
    return contents

def validate_openapi_yaml(yaml_content):
    """Validate the OpenAPI YAML content."""
    try:
        # Parse YAML to ensure it's syntactically correct
        yaml.safe_load(yaml_content)
        # Basic OpenAPI 3.0 validation (checking required fields)
        parsed = yaml.safe_load(yaml_content)
        if not isinstance(parsed, dict) or "openapi" not in parsed or "info" not in parsed or "paths" not in parsed:
            return False, "Missing required OpenAPI fields (openapi, info, paths)"
        return True, None
    except yaml.YAMLError as e:
        return False, f"YAML parsing error: {e}"
    except Exception as e:
        return False, f"Unexpected validation error: {e}"

def create_project_zip(service_name, files_dict):
    """Create a ZIP file with a structure for Boomi APIM integration."""
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    zip_path = f"{output_dir}/{service_name}_boomi_integration.zip"
    project_root = f"{service_name}-boomi-integration"
    
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path, content in files_dict.items():
            # Adjust file path for ZIP structure
            full_path = os.path.join(project_root, file_path)
            temp_path = os.path.join(output_dir, full_path)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, "w") as f:
                f.write(content)
            zipf.write(temp_path, full_path)
            os.remove(temp_path)
    
    with open(zip_path, "rb") as f:
        st.download_button(
            label=f"Download {service_name} Boomi Integration ZIP",
            data=f,
            file_name=f"{service_name}_boomi_integration.zip",
            mime="application/zip"
        )