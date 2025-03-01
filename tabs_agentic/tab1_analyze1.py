import streamlit as st
from utils.agentic_helper import run_agentic_workflow
from utils.file_helper import create_zip_download
import os
import zipfile
import streamlit.components.v1 as components

def analyze_webmethods():
    # File uploader
    flow_files = st.file_uploader("Upload webMethods flow files (e.g., flow.xml or flow.html)", type=["xml", "html"], accept_multiple_files=True, key="tab1_uploader")
    
    # Analysis preferences
    st.subheader("Analysis Preferences")
    granularity = st.selectbox("Microservices Granularity", options=["Coarse", "Fine", "Balanced"], index=2, key="tab1_granularity")
    focus_area = st.multiselect("Focus Areas", options=["Data Structures", "Business Logic", "Integrations"], default=["Data Structures", "Business Logic"], key="tab1_focus_area")

    # Visual workflow graph
    st.subheader("Agentic Workflow Overview")
    st.markdown("This tab uses a stateful, graph-based workflow powered by LangGraph. Explore the process below!")
    
    # Define the full workflow graph (for visualization)
    workflow_graph = """
    digraph G {
        rankdir=LR;
        analyze [label="Analyze (Tab 1)", shape=box, style=filled, fillcolor=lightblue];
        design [label="Design (Tab 2)", shape=box];
        generate [label="Generate (Tab 3)", shape=box];
        boomi [label="Boomi APIM (Tab 4)", shape=box];
        tests [label="Tests (Tab 5)", shape=box];
        migrate [label="Migrate (Tab 6)", shape=box];
        howto [label="HowTo (Tab 7)", shape=box];
        analyze -> design -> generate -> boomi -> tests -> migrate -> howto;
    }
    """
    # Placeholder for dynamic graph updates
    graph_placeholder = st.empty()
    graph_placeholder.graphviz_chart(workflow_graph, use_container_width=True)

    # Workflow execution
    if st.button("Analyze", key="tab1_analyze"):
        st.session_state.progress["tab1"] = "In Progress"
        st.write("Starting analysis...")

        if flow_files:
            flow_contents = []
            for flow_file in flow_files:
                content = flow_file.read().decode("utf-8")
                file_type = "xml" if flow_file.name.endswith(".xml") else "html"
                flow_contents.append(f"{file_type.upper()} Content:\n{content}")
            
            # Prepare input data
            input_data = "\n---\n".join(flow_contents)
            inputs = {
                "tab1": input_data,
                "tab2": "", "tab3": "", "tab4": "", "tab5": "", "tab6": "", "tab7": ""
            }
            
            # Run the agentic workflow with reasoning steps
            with st.expander("Agent Reasoning Steps", expanded=True):
                st.markdown("### Agentic Workflow Execution")
                st.write("The agentic AI processes your request through a graph of nodes. Track its progress below:")
                
                # Simulate node execution with visibility
                st.markdown("**Node: Analyze (Tab 1)**")
                st.write("Processing input files to extract structured content...")
                outputs = run_agentic_workflow(inputs, "tab1")
                st.write("Analysis complete!")
                
                # Update graph to highlight completed node
                updated_graph = """
                digraph G {
                    rankdir=LR;
                    analyze [label="Analyze (Tab 1)", shape=box, style=filled, fillcolor=green];
                    design [label="Design (Tab 2)", shape=box];
                    generate [label="Generate (Tab 3)", shape=box];
                    boomi [label="Boomi APIM (Tab 4)", shape=box];
                    tests [label="Tests (Tab 5)", shape=box];
                    migrate [label="Migrate (Tab 6)", shape=box];
                    howto [label="HowTo (Tab 7)", shape=box];
                    analyze -> design -> generate -> boomi -> tests -> migrate -> howto;
                }
                """
                graph_placeholder.graphviz_chart(updated_graph, use_container_width=True)

            # State inspector
            with st.expander("Workflow State Inspector", expanded=False):
                st.markdown("### Current Workflow State")
                st.write("The agentic AI maintains state across tabs. Here’s the current state:")
                st.json({"inputs": inputs, "outputs": outputs})

            # Parse and display response
            files_dict = parse_ai_response_to_files(outputs.get("tab1", "No output generated"))
            if not files_dict:
                st.error("No Markdown content parsed from agent response.")
            else:
                st.session_state.progress["tab1"] = "Completed"
                st.markdown("### Generated Microservices Suggestions")
                for file_path, content in files_dict.items():
                    st.subheader(file_path)
                    st.markdown(content)
                
                # Interactive step navigation
                st.subheader("Explore Workflow Outputs")
                step = st.selectbox("Select a step to inspect", options=["Analyze Output"], key="tab1_step_select")
                if step == "Analyze Output":
                    st.markdown("**Analyze Node Output**")
                    st.markdown(files_dict.get("microservices_suggestion.md", "No output available."))

                # Create downloadable ZIP
                create_project_zip(files_dict)
        else:
            st.warning("Please upload at least one flow file.")
            st.session_state.progress["tab1"] = "Not Started"
    
    st.text(f"Progress: {st.session_state.progress['tab1']}")

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

if __name__ == "__main__":
    analyze_webmethods()