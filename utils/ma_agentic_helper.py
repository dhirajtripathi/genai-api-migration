from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
#from langchain.embeddings import SentenceTransformerEmbeddings
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.document_loaders import PyPDFLoader
import os
from bs4 import BeautifulSoup
from typing import TypedDict, Dict, Any, List
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
from graphviz import Source

load_dotenv()

# Initialize LLM with Gemini
G_API_KEY = "AIzaSyBQmEldQBkdJ9QDszc-NdFYvl_3VGAEsjs"  # Replace with your actual Google API key
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=G_API_KEY, temperature=0.3)

# Define state structure
class TransformationState(TypedDict):
    inputs: Dict[str, Any]  # User inputs per tab
    outputs: Dict[str, str]  # Generated outputs per tab
    current_agent: str      # Current agent being executed
    context: str            # Retrieved documentation context
    plan: Dict[str, str]    # Plan from supervisor agent
    task_queue: List[str]   # Queue of agents to execute

# Tool for parsing files
def parse_file(content: str, file_type: str) -> str:
    if file_type == "xml":
        try:
            root = ET.fromstring(content)
            return ET.tostring(root, encoding="unicode")
        except Exception as e:
            return f"Error parsing XML: {e}"
    elif file_type == "html":
        soup = BeautifulSoup(content, "html.parser")
        return str(soup)
    return "Unsupported file type"

tools = [Tool(name="parse_file", func=parse_file, description="Parse XML or HTML content.")]

# RAG Setup
vector_store = None

def setup_vector_store(directory: str = "webmethods_docs"):
    """Load and chunk webMethods documentation PDFs, returning a FAISS vector store or None if empty."""
    global vector_store
    if vector_store is not None:
        return vector_store
    
    docs = []
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            if filename.endswith(".pdf"):
                loader = PyPDFLoader(os.path.join(directory, filename))
                docs.extend(loader.load())
    
    if not docs:
        return None
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(docs)
    if not chunks:
        return None
    
    embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    vector_store = FAISS.from_documents(chunks, embeddings)
    return vector_store

def retrieve_context(query: str) -> str:
    vector_store = setup_vector_store()
    if vector_store:
        docs = vector_store.similarity_search(query, k=3)
        return "\n".join([doc.page_content for doc in docs])
    return "No documentation available."

# Supervisor Agent
def supervisor_agent(state: TransformationState) -> TransformationState:
    """Supervisor agent plans the transformation and assigns tasks."""
    if state["plan"]:
        return state  # Plan already generated
    
    prompt = state["inputs"]["tab1"]  # Assuming tab1 holds the initial prompt
    context = retrieve_context("webMethods transformation to microservices")
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
    ).format(prompt=prompt, context=context)
    response = llm.invoke(plan_prompt).content
    
    try:
        import json
        plan = json.loads(response)
    except:
        plan = {}
    
    state["plan"] = plan
    state["task_queue"] = ["analyzer", "designer", "generator", "boomi_integrator", "tester", "migrator", "howto_writer"]
    state["current_agent"] = "analyzer"
    return state

# Specialized Agents
def analyzer_agent(state: TransformationState) -> TransformationState:
    if state["current_agent"] != "analyzer":
        return state
    context = retrieve_context("webMethods integration services analysis")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Analyze webMethods flow files: {inputs}. Suggest a microservices architecture with:\n"
        "- Summary\n- Suggested Microservices (Name, Responsibilities, Endpoints, Data Entities)\n- Dependencies\n- Insights\n- Diagram (Mermaid)\n"
        "Output as `### microservices_suggestion.md`."
    ).format(inputs=state["inputs"]["tab1"], context=context)
    response = llm.invoke(prompt).content
    state["outputs"]["tab1"] = response
    state["context"] = context
    state["task_queue"].pop(0)
    state["current_agent"] = state["task_queue"][0] if state["task_queue"] else "end"
    return state

def designer_agent(state: TransformationState) -> TransformationState:
    if state["current_agent"] != "designer":
        return state
    context = retrieve_context("Spring Boot microservices design")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Design a microservices architecture for Spring Boot and Boomi APIM based on: {inputs}. Include:\n"
        "- Overview\n- Microservices Breakdown\n- Communication Patterns\n- Deployment Considerations\n- Boomi APIM Integration\n- Diagram (Mermaid)\n"
        "Output as `### architecture.md`.\n"
        "Use Tab 1 output: {tab1_output}"
    ).format(inputs=state["inputs"]["tab2"], context=context, tab1_output=state["outputs"]["tab1"])
    response = llm.invoke(prompt).content
    state["outputs"]["tab2"] = response
    state["context"] = context
    state["task_queue"].pop(0)
    state["current_agent"] = state["task_queue"][0] if state["task_queue"] else "end"
    return state

def generator_agent(state: TransformationState) -> TransformationState:
    if state["current_agent"] != "generator":
        return state
    context = retrieve_context("Spring Boot code generation")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Generate a Spring Boot microservice project based on: {inputs}. Include:\n"
        "- `pom.xml`: Maven config with Spring Boot dependencies.\n"
        "- `src/main/java/com/example/default/controller/DefaultController.java`: REST controller with 2 endpoints (GET, POST).\n"
        "- `src/main/java/com/example/default/service/DefaultService.java`: Service layer.\n"
        "- `src/main/java/com/example/default/entity/DefaultEntity.java`: Entity class with JPA.\n"
        "- `src/main/resources/application.yml`: Config file.\n"
        "Output each file prefixed with its path (e.g., `### pom.xml`).\n"
        "Use Tab 2 output: {tab2_output}"
    ).format(inputs=state["inputs"]["tab3"], context=context, tab2_output=state["outputs"]["tab2"])
    response = llm.invoke(prompt).content
    state["outputs"]["tab3"] = response
    state["context"] = context
    state["task_queue"].pop(0)
    state["current_agent"] = state["task_queue"][0] if state["task_queue"] else "end"
    return state

def boomi_integrator_agent(state: TransformationState) -> TransformationState:
    if state["current_agent"] != "boomi_integrator":
        return state
    context = retrieve_context("Boomi APIM integration")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Generate an OpenAPI 3.0 YAML file and Boomi APIM instructions based on: {inputs}. Include:\n"
        "- `openapi.yaml`: OpenAPI spec with 2 endpoints (GET, POST), schemas, and Boomi policies.\n"
        "- `README.md`: Instructions for importing into Boomi APIM.\n"
        "Output each file prefixed with its path (e.g., `### openapi.yaml`).\n"
        "Use Tab 3 output: {tab3_output}"
    ).format(inputs=state["inputs"]["tab4"], context=context, tab3_output=state["outputs"]["tab3"])
    response = llm.invoke(prompt).content
    state["outputs"]["tab4"] = response
    state["context"] = context
    state["task_queue"].pop(0)
    state["current_agent"] = state["task_queue"][0] if state["task_queue"] else "end"
    return state

def tester_agent(state: TransformationState) -> TransformationState:
    if state["current_agent"] != "tester":
        return state
    context = retrieve_context("JUnit testing for Spring Boot")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Generate JUnit 5 test cases for a Spring Boot microservice based on: {inputs}. Include:\n"
        "- `pom.xml`: Maven config with test dependencies.\n"
        "- `src/test/java/com/example/default/controller/DefaultControllerTest.java`: Controller tests with @WebMvcTest.\n"
        "- `src/test/java/com/example/default/service/DefaultServiceTest.java`: Service tests with @SpringBootTest.\n"
        "Output each file prefixed with its path (e.g., `### pom.xml`).\n"
        "Use Tab 3 output: {tab3_output}"
    ).format(inputs=state["inputs"]["tab5"], context=context, tab3_output=state["outputs"]["tab3"])
    response = llm.invoke(prompt).content
    state["outputs"]["tab5"] = response
    state["context"] = context
    state["task_queue"].pop(0)
    state["current_agent"] = state["task_queue"][0] if state["task_queue"] else "end"
    return state

def migrator_agent(state: TransformationState) -> TransformationState:
    if state["current_agent"] != "migrator":
        return state
    context = retrieve_context("webMethods to Spring Boot migration")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Generate a migration plan and code to transform webMethods data and logic into a Spring Boot microservice based on: {inputs}. Include:\n"
        "- `migration.md`: Detailed step-by-step migration instructions.\n"
        "- `src/main/java/com/example/default/migration/DefaultMigration.java`: Java class with migration code.\n"
        "Output each file prefixed with its path (e.g., `### migration.md`).\n"
        "Use Tab 3 output: {tab3_output}"
    ).format(inputs=state["inputs"]["tab6"], context=context, tab3_output=state["outputs"]["tab3"])
    response = llm.invoke(prompt).content
    state["outputs"]["tab6"] = response
    state["context"] = context
    state["task_queue"].pop(0)
    state["current_agent"] = state["task_queue"][0] if state["task_queue"] else "end"
    return state

def howto_writer_agent(state: TransformationState) -> TransformationState:
    if state["current_agent"] != "howto_writer":
        return state
    context = retrieve_context("webMethods to microservices transformation guide")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Generate a HowTo guide for transforming webMethods to microservices based on: {inputs}. Include:\n"
        "- Introduction: Overview of the process.\n"
        "- Step-by-Step Instructions: Detailed steps for analysis, design, code generation, API integration, testing, and migration.\n"
        "- Best Practices: Tips for success.\n"
        "Output as `### howto.md`.\n"
        "Consolidate outputs from Tabs 1-6: {all_outputs}"
    ).format(inputs=state["inputs"]["tab7"], context=context, all_outputs="\n".join([f"{tab}: {state['outputs'][tab]}" for tab in state["outputs"]]))
    response = llm.invoke(prompt).content
    state["outputs"]["tab7"] = response
    state["context"] = context
    state["task_queue"].pop(0)
    state["current_agent"] = "end"
    return state

# Define graph
workflow = StateGraph(TransformationState)

# Add nodes (agents)
workflow.add_node("supervisor", supervisor_agent)
workflow.add_node("analyzer", analyzer_agent)
workflow.add_node("designer", designer_agent)
workflow.add_node("generator", generator_agent)
workflow.add_node("boomi_integrator", boomi_integrator_agent)
workflow.add_node("tester", tester_agent)
workflow.add_node("migrator", migrator_agent)
workflow.add_node("howto_writer", howto_writer_agent)

# Define edges
workflow.add_edge("supervisor", "analyzer")
workflow.add_edge("analyzer", "designer")
workflow.add_edge("designer", "generator")
workflow.add_edge("generator", "boomi_integrator")
workflow.add_edge("boomi_integrator", "tester")
workflow.add_edge("tester", "migrator")
workflow.add_edge("migrator", "howto_writer")
workflow.add_edge("howto_writer", END)

# Set entry point
workflow.set_entry_point("supervisor")

# Compile graph
graph = workflow.compile()

# Generate graph image
def generate_graph_image(current_agent: str) -> str:
    dot = "digraph G {\nrankdir=LR;\n"
    nodes = ["supervisor", "analyzer", "designer", "generator", "boomi_integrator", "tester", "migrator", "howto_writer"]
    tab_map = {
        "supervisor": "Supervisor",
        "analyzer": "Analyzer (Tab 1)",
        "designer": "Designer (Tab 2)",
        "generator": "Generator (Tab 3)",
        "boomi_integrator": "Boomi Integrator (Tab 4)",
        "tester": "Tester (Tab 5)",
        "migrator": "Migrator (Tab 6)",
        "howto_writer": "HowTo Writer (Tab 7)"
    }

    for node in nodes:
        fillcolor = "green" if node == current_agent else "lightblue"
        dot += f'{node} [label="{tab_map[node]}", shape=box, style=filled, fillcolor={fillcolor}];\n'
    
    for i in range(len(nodes) - 1):
        dot += f"{nodes[i]} -> {nodes[i+1]};\n"
    dot += "}"

    graph_file = Source(dot, filename="workflow", format="png")
    graph_file.render(cleanup=True)
    return "workflow.png"

def run_agentic_workflow(inputs: Dict[str, Any], current_tab: str) -> Dict[str, str]:
    initial_state = {
        "inputs": inputs,
        "outputs": {},
        "current_agent": "supervisor",
        "context": "",
        "plan": {},
        "task_queue": []
    }
    result = graph.invoke(initial_state)
    #generate_graph_image(result["current_agent"])
    return result["outputs"]