import streamlit as st
from utils.ai_helper import get_ai_response
from utils.file_helper import create_zip_download

def generate_howto():
    # Upload artifacts (e.g., all previous outputs)
    previous_outputs = st.file_uploader(
        "Upload previous outputs (e.g., from Tabs 1-6)", 
        type=["md", "java", "yaml", "txt"], 
        accept_multiple_files=True, 
        key="tab7_uploader"
    )

    if st.button("Generate HowTo", key="tab7_generate"):
        st.session_state.progress["tab7"] = "In Progress"
        prompt = "Generate a step-by-step HowTo guide in Markdown for transforming webMethods to microservices."
        if previous_outputs:
            output_contents = [file.read().decode("utf-8") for file in previous_outputs]
            prompt += f"\nBased on these outputs:\n{'---'.join(output_contents)}"
        response = get_ai_response(prompt)
        st.session_state.progress["tab7"] = "Completed"
        st.markdown("### HowTo Instructions")
        st.markdown(response)
        create_zip_download("tab7_output", {"howto.md": response})
    
    st.text(f"Progress: {st.session_state.progress['tab7']}")