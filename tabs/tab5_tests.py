import streamlit as st
from utils.ai_helper import get_ai_response
from utils.file_helper import create_zip_download
import os
import zipfile

def generate_unit_tests():
    # Upload artifacts (e.g., microservice code from Tab 3)
    code_file = st.file_uploader(
        "Upload microservice code (e.g., from Tab 3)", 
        type=["java", "txt"], 
        key="tab5_uploader"
    )

    # User input for service name (to match Tab 3 structure)
    service_name = st.text_input(
        "Service Name (e.g., OrderService, must match microservice from Tab 3)", 
        value="SampleService", 
        key="tab5_service_name"
    )

    if st.button("Generate Tests", key="tab5_generate"):
        st.session_state.progress["tab5"] = "In Progress"
        
        # Prepare the prompt
        base_prompt = (
            "Generate a complete set of JUnit 5 test cases for a Spring Boot microservice project with the following structure:\n"
            "- `pom.xml`: Maven configuration with Spring Boot test dependencies (e.g., spring-boot-starter-test, JUnit 5, Mockito).\n"
            "- `src/test/java/com/example/{service_name}/controller/{ServiceName}ControllerTest.java`: Controller tests using @WebMvcTest and Mockito.\n"
            "- `src/test/java/com/example/{service_name}/service/{ServiceName}ServiceTest.java`: Service tests using @SpringBootTest and Mockito.\n"
            "Replace `{service_name}` with the provided service name in lowercase and `{ServiceName}` with its CamelCase version.\n"
            "Include at least 2 test cases per class (e.g., success and failure scenarios).\n"
            "Provide the content of each file as a separate section in the response, prefixed with the file path (e.g., `### pom.xml`)."
        )
        
        # Incorporate uploaded code if provided
        if code_file:
            code_content = code_file.read().decode("utf-8")
            prompt = f"{base_prompt}\nGenerate tests for this microservice code:\n{code_content}"
        else:
            prompt = base_prompt + "\nGenerate tests for a generic Spring Boot microservice with a controller and service layer."
        
        # Add service name to prompt
        prompt += f"\nService Name: {service_name}"

        # Get AI response
        response = get_ai_response(prompt)

        #RAG version
        # response = get_ai_response(prompt, use_rag=True)        
        
        # Parse the response into files
        files_dict = parse_ai_response_to_files(response, service_name)
        
        # Display generated test code
        st.session_state.progress["tab5"] = "Completed"
        st.markdown("### Generated Unit Test Files")
        for file_path, content in files_dict.items():
            st.subheader(file_path)
            st.code(content, language="java" if file_path.endswith(".java") else "xml")
        
        # Create ZIP with project structure
        create_project_zip(service_name, files_dict)
    
    st.text(f"Progress: {st.session_state.progress['tab5']}")

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

def create_project_zip(service_name, files_dict):
    """Create a ZIP file with a Maven project structure for tests."""
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    zip_path = f"{output_dir}/{service_name}_test_project.zip"
    project_root = f"{service_name}-test-project"
    
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path, content in files_dict.items():
            # Adjust file path to match Maven test structure
            full_path = os.path.join(project_root, file_path)
            temp_path = os.path.join(output_dir, full_path)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, "w") as f:
                f.write(content)
            zipf.write(temp_path, full_path)
            os.remove(temp_path)
    
    with open(zip_path, "rb") as f:
        st.download_button(
            label=f"Download {service_name} Test Project ZIP",
            data=f,
            file_name=f"{service_name}_test_project.zip",
            mime="application/zip"
        )