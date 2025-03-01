import streamlit as st
from dotenv import load_dotenv
from tabs.tab1_analyze import analyze_webmethods
from tabs.tab2_design import design_architecture
from tabs.tab3_generate import generate_microservices
from tabs.tab4_boomi import boomi_apim_integration
from tabs.tab5_tests import generate_unit_tests
from tabs.tab6_migrate import migrate_data_logic
from tabs.tab7_howto import generate_howto

# Load environment variables
load_dotenv()

# Streamlit app configuration
st.set_page_config(page_title="Legacy to Microservices Transformer", layout="wide")

# Initialize session state for progress tracking
if "progress" not in st.session_state:
    st.session_state.progress = {f"tab{i}": "Not Started" for i in range(1, 8)}

# Define tabs
tabs = st.tabs([
    "Analyze webMethods",
    "Design Architecture",
    "Generate Microservices",
    "Boomi APIM Integration",
    "Unit Tests",
    "Migrate Data & Logic",
    "HowTo Instructions"
])

# Tab 1: Analyze webMethods
with tabs[0]:
    st.header("Analyze webMethods")
    analyze_webmethods()

# Tab 2: Design Architecture
with tabs[1]:
    st.header("Design Architecture")
    design_architecture()

# Tab 3: Generate Microservices
with tabs[2]:
    st.header("Generate Microservices")
    generate_microservices()

# Tab 4: Boomi APIM Integration
with tabs[3]:
    st.header("Boomi APIM Integration")
    boomi_apim_integration()

# Tab 5: Unit Tests
with tabs[4]:
    st.header("Unit Tests")
    generate_unit_tests()

# Tab 6: Migrate Data & Logic
with tabs[5]:
    st.header("Migrate Data & Logic")
    migrate_data_logic()

# Tab 7: HowTo Instructions
with tabs[6]:
    st.header("HowTo Instructions")
    generate_howto()