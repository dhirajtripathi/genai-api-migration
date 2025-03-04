import streamlit as st
from utils.ma_agentic_helper import run_agentic_workflow, llm, vector_store, graph
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
import zipfile
from typing import Dict
import logging
import time

# Load environment variables
load_dotenv()

# Set up logging
# Set up logging
logging.basicConfig(
    filename="debug.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Streamlit page configuration
st.set_page_config(page_title="Multi-Agent AI Transformer", layout="wide")

# Initialize session state
if "progress" not in st.session_state:
    st.session_state.progress = {f"tab{i}": "Not Started" for i in range(1, 8)}
if "workflow_outputs" not in st.session_state:
    st.session_state.workflow_outputs = {}
if "workflow_state" not in st.session_state:
    st.session_state.workflow_state = {}

def generate_plan(prompt: str) -> Dict[str, str]:
    """Generate a plan based on the user's natural language prompt with RAG."""
    context = vector_store.similarity_search("webMethods transformation to microservices", k=3) if vector_store else []
    context_text = "\n".join([doc.page_content for doc in context]) if context else "No documentation available."
    plan_prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Given the user prompt: '{prompt}', generate a plan to transform webMethods integration services into cloud-native microservices using Spring Boot. "
        "Map the plan to the following agents: Analyzer (tab1), Designer (tab2), Generator (tab3), BoomiIntegrator (tab4), Tester (tab5), Migrator (tab6), HowToWriter (tab7). "
        "For each agent, provide a brief description of what it will do. Output as a valid JSON string and NOTHING ELSE:\n"
        "{{\n"
        "  \"tab1\": \"description for Analyzer\",\n"
        "  \"tab2\": \"description for Designer\",\n"
        "  \"tab3\": \"description for Generator\",\n"
        "  \"tab4\": \"description for BoomiIntegrator\",\n"
        "  \"tab5\": \"description for Tester\",\n"
        "  \"tab6\": \"description for Migrator\",\n"
        "  \"tab7\": \"description for HowToWriter\"\n"
        "}}"
    ).format(prompt=prompt, context=context_text)
    response = llm.invoke(plan_prompt).content
    logger.debug(f"LLM response for plan: {response}")
    
    try:
        import json
        return json.loads(response)
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}. Raw response: {response}")
        if "tab1" in response:
            try:
                start = response.find("{")
                end = response.rfind("}") + 1
                if start != -1 and end != -1:
                    json_str = response[start:end]
                    return json.loads(json_str)
            except:
                pass
        return {}

def execute_full_workflow(inputs: dict, uploaded_files: list):
    """Execute the multi-agent LangGraph workflow with RAG and UI updates."""
    tabs = ["tab1", "tab2", "tab3", "tab4", "tab5", "tab6", "tab7"]
    agents = ["analyzer", "designer", "generator", "boomi_integrator", "tester", "migrator", "howto_writer"]
    outputs = {}
    
    if uploaded_files:
        flow_contents = []
        for flow_file in uploaded_files:
            content = flow_file.read().decode("utf-8")
            file_type = "xml" if flow_file.name.endswith(".xml") else "html"
            flow_contents.append(f"{file_type.upper()} Content:\n{content}")
        inputs["tab1"] = "\n---\n".join(flow_contents)
    
    progress_bar = st.progress(0)
    status_placeholder = st.empty()
    state_placeholder = st.empty()

    # Execute supervisor first
    status_placeholder.write("Supervisor Agent planning the transformation...")
    time.sleep(1)
    initial_state = {"inputs": inputs, "outputs": {}, "current_agent": "supervisor", "context": "", "plan": {}, "task_queue": []}
    result = graph.invoke(initial_state)
    plan = result["plan"]
    outputs.update(result["outputs"])
    st.session_state.workflow_state = result

    for i, agent in enumerate(agents):
        tab = tabs[i]
        st.session_state.progress[tab] = "In Progress"
        status_placeholder.write(f"{agent.capitalize()} Agent executing {tab.capitalize()}...")
        progress_bar.progress((i + 1) / len(agents))
        
        time.sleep(1)  # Simulated delay for visibility
        
        tab_outputs = run_agentic_workflow(inputs, tab)
        outputs.update(tab_outputs)
        inputs[tab] = ""  # Clear input for this tab after processing
        st.session_state.progress[tab] = "Completed"
        st.session_state.workflow_outputs[tab] = tab_outputs.get(tab, "No output generated")
        
        # Update state display
        state_placeholder.json({
            "inputs": inputs,
            "outputs": st.session_state.workflow_outputs,
            "current_agent": agent,
            "rag_context": tab_outputs.get("context", "No context available"),
            "plan": plan
        })
    
    status_placeholder.write("Multi-Agent Workflow completed successfully!")
    return outputs


def main():
    st.title("Multi-Agent AI Transformer with RAG")
    st.markdown("""
        **Multi-Agent Power**: This system uses a team of specialized agents, orchestrated by a Supervisor Agent, to transform your webMethods services:
        - **Supervisor Agent**: Plans and delegates tasks based on your prompt.
        - **Specialized Agents**: Collaborate to analyze, design, generate code, integrate APIs, test, migrate, and document—each with RAG-enhanced intelligence.
        - **Stateful Workflow**: Agents share context and outputs, ensuring a cohesive transformation.
        Enter your request below and watch the agents work together!
    """)

    # Prompt input
    prompt = st.text_area("Your Request", "e.g., 'analyze my webMethods integration services and transform them to cloud-native microservices based on Spring Boot'", height=100)
    uploaded_files = st.file_uploader("Upload webMethods flow files (optional)", type=["xml", "html"], accept_multiple_files=True, key="prompt_uploader")

    # Workflow visualization
    st.subheader("Multi-Agent Workflow Pipeline")
    st.markdown("The Supervisor Agent coordinates these specialized agents:")
    workflow_steps = """
    ```mermaid
    graph LR
        S[Supervisor] --> A[Analyzer<br>(Tab 1)]
        A --> D[Designer<br>(Tab 2)]
        D --> G[Generator<br>(Tab 3)]
        G --> B[Boomi Integrator<br>(Tab 4)]
        B --> T[Tester<br>(Tab 5)]
        T --> M[Migrator<br>(Tab 6)]
        M --> H[HowTo Writer<br>(Tab 7)]
    """
    st.markdown(workflow_steps)
    if st.button("Transform"):
        if prompt:
            with st.spinner("Supervisor Agent generating plan with RAG..."):
                inputs = {f"tab{i+1}": "" for i in range(7)}
                inputs["tab1"] = prompt  # Pass prompt to supervisor via tab1
                plan = generate_plan(prompt)
                if not plan:
                    st.error("Failed to generate a valid plan. Please try again.")
                    st.write("Raw LLM response (for debugging):")
                    if os.path.exists("debug.log"):
                        with open("debug.log", "r") as f:
                            st.text(f.read())
                    else:
                        st.text("Debug log not available yet.")
                    return


                st.subheader("Transformation Plan (RAG-Enhanced)")
                st.markdown("The Supervisor Agent crafted this plan, assigning tasks to specialized agents:")
                st.json(plan)

            st.subheader("Multi-Agent Execution")
            st.markdown("Watch the agents collaborate, each enhancing the process with RAG and state sharing:")
            outputs = execute_full_workflow(inputs, uploaded_files)

            st.subheader("Transformation Results")
            st.markdown("Here’s the collective output from our multi-agent team:")
            for tab, output in st.session_state.workflow_outputs.items():
                with st.expander(f"{tab.upper()} Output (Agent: {tab_to_agent(tab)})", expanded=False):
                    files_dict = parse_ai_response_to_files(output)
                    for file_path, content in files_dict.items():
                        st.subheader(file_path)
                        st.markdown(content)

            # Generate a combined ZIP of all outputs
            create_combined_zip(st.session_state.workflow_outputs)


def tab_to_agent(tab: str) -> str:
    mapping = {
        "tab1": "Analyzer",
        "tab2": "Designer",
        "tab3": "Generator",
        "tab4": "Boomi Integrator",
        "tab5": "Tester",
        "tab6": "Migrator",
        "tab7": "HowTo Writer"
    }
    return mapping.get(tab, "Unknown")

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

def create_combined_zip(outputs):
    """Create a ZIP file with all tab outputs."""
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    zip_path = f"{output_dir}/transformation_result.zip"
    project_root = "transformation"

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for tab, output in outputs.items():
            files_dict = parse_ai_response_to_files(output)
            for file_path, content in files_dict.items():
                full_path = os.path.join(project_root, tab, file_path)
                temp_path = os.path.join(output_dir, full_path)
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                with open(temp_path, "w") as f:
                    f.write(content)
                zipf.write(temp_path, full_path)
                os.remove(temp_path)

    with open(zip_path, "rb") as f:
        st.download_button(
            label="Download Transformation Result ZIP",
            data=f,
            file_name="transformation_result.zip",
            mime="application/zip"
        )

           

if __name__ == "__main__":
    main()
