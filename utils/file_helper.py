import os
import zipfile
import streamlit as st

def create_zip_download(output_name, files_dict):
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    zip_path = f"{output_dir}/{output_name}.zip"
    
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for filename, content in files_dict.items():
            file_path = f"{output_dir}/{filename}"
            with open(file_path, "w") as f:
                f.write(content)
            zipf.write(file_path, filename)
            os.remove(file_path)
    
    with open(zip_path, "rb") as f:
        st.download_button(
            label=f"Download {output_name}.zip",
            data=f,
            file_name=f"{output_name}.zip",
            mime="application/zip"
        )