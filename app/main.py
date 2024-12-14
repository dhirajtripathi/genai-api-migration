import streamlit as st
from app.ui.tab1 import tab1_ui
from app.ui.tab2 import tab2_ui
from app.ui.tab3 import tab3_ui

def main():
    st.set_page_config(page_title="API Migration Tool", layout="wide")
    tabs = ["Swagger to OpenAPI 3", "Generate Microservices", "Create Unit Tests"]
    tab = st.sidebar.radio("Select Tab", tabs)

    if tab == "Swagger to OpenAPI 3":
        tab1_ui()
    elif tab == "Generate Microservices":
        tab2_ui()
    elif tab == "Create Unit Tests":
        tab3_ui()

if __name__ == "__main__":
    main()
