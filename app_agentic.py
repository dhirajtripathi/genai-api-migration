import streamlit as st
from tabs_agentic.tab1_analyze import analyze_webmethods
from tabs_agentic.tab2_design import design_architecture
from tabs_agentic.tab3_generate import generate_microservices
from tabs_agentic.tab4_boomi import boomi_apim_integration
from tabs_agentic.tab5_tests import generate_unit_tests
from tabs_agentic.tab6_migrate import migrate_data_logic
from tabs_agentic.tab7_howto import generate_howto
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Agentic AI Legacy to Microservices Transformer", layout="wide")

if "progress" not in st.session_state:
    st.session_state.progress = {f"tab{i}": "Not Started" for i in range(1, 8)}

tabs = st.tabs([
    "Analyze webMethods", "Design Architecture", "Generate Microservices",
    "Boomi APIM Integration", "Unit Tests", "Migrate Data & Logic", "HowTo Instructions"
])

with tabs[0]:
    st.header("Analyze webMethods")
    analyze_webmethods()
with tabs[1]:
    st.header("Design Architecture")
    design_architecture()
with tabs[2]:
    st.header("Generate Microservices")
    generate_microservices()
with tabs[3]:
    st.header("Boomi APIM Integration")
    boomi_apim_integration()
with tabs[4]:
    st.header("Unit Tests")
    generate_unit_tests()
with tabs[5]:
    st.header("Migrate Data & Logic")
    migrate_data_logic()
with tabs[6]:
    st.header("HowTo Instructions")
    generate_howto()

if __name__ == "__main__":
    st.write("Agentic AI Transformation Pipeline Ready")