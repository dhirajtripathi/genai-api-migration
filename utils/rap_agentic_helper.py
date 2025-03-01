from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain_community.document_loaders import PyPDFLoader
import os
from bs4 import BeautifulSoup
from typing import TypedDict, Annotated, Dict, Any
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
from graphviz import Source

load_dotenv()

# Initialize LLM with Gemini
G_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    api_key=G_API_KEY,
    temperature=0.3
)

# Load and prepare RAG with webMethods documentation
def load_webmethods_docs(directory: str = "webmethods_docs"):
    """Load and chunk webMethods documentation PDFs."""
    docs = []
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            if filename.endswith(".pdf"):
                loader = PyPDFLoader(os.path.join(directory, filename))
                docs.extend(loader.load())
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(docs)
    
    embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")  # Free embeddings
    vector_store = FAISS.from_documents(chunks, embeddings)
    return vector_store

# Initialize vector store (run once or on demand)
vector_store = load_webmethods_docs()

# Define state structure
class TransformationState(TypedDict):
    inputs: Dict[str, Any]  # User inputs per tab
    outputs: Dict[str, str]  # Generated outputs per tab
    current_tab: str        # Current tab being processed
    context: str            # Retrieved documentation context

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

tools = [
    Tool(name="parse_file", func=parse_file, description="Parse XML or HTML content.")
]

# Retrieve context from documentation
def retrieve_context(query: str) -> str:
    if vector_store:
        docs = vector_store.similarity_search(query, k=3)
        return "\n".join([doc.page_content for doc in docs])
    return "No documentation available."

# Node functions with RAG
def analyze_node(state: TransformationState) -> TransformationState:
    if state["current_tab"] != "tab1":
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
    return state

def design_node(state: TransformationState) -> TransformationState:
    if state["current_tab"] != "tab2":
        return state
    context = retrieve_context("Spring Boot microservices design")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Design a microservices architecture for Spring Boot and Boomi APIM based on: {inputs}. Include:\n"
        "- Overview\n- Microservices Breakdown\n- Communication Patterns\n- Deployment Considerations\n- Boomi APIM Integration\n- Diagram (Mermaid)\n"
        "Output as `### architecture.md`.\n"
        "If Tab 1 output is available, use it to inform the design."
    ).format(inputs=state["inputs"]["tab2"] + (f"\nTab 1 Output:\n{state['outputs']['tab1']}" if "tab1" in state["outputs"] else ""), context=context)
    response = llm.invoke(prompt).content
    state["outputs"]["tab2"] = response
    state["context"] = context
    return state

def generate_node(state: TransformationState) -> TransformationState:
    if state["current_tab"] != "tab3":
        return state
    context = retrieve_context("Spring Boot code generation")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Generate a Spring Boot microservice project based on: {inputs}. Include:\n"
        "- `pom.xml`: Maven configuration with Spring Boot dependencies.\n"
        "- `src/main/java/com/example/{service_name}/controller/{ServiceName}Controller.java`: REST controller with 2 endpoints (GET, POST).\n"
        "- `src/main/java/com/example/{service_name}/service/{ServiceName}Service.java`: Service layer.\n"
        "- `src/main/java/com/example/{service_name}/entity/{ServiceName}Entity.java`: Entity class with JPA.\n"
        "- `src/main/resources/application.yml`: Configuration file.\n"
        "Output each file prefixed with its path (e.g., `### pom.xml`).\n"
        "If Tab 2 output is available, use it to inform the design."
    ).format(
        inputs=state["inputs"]["tab3"],
        service_name=state["inputs"]["tab3"].split("Microservice Name: ")[1].split("\n")[0].lower() if "Microservice Name: " in state["inputs"]["tab3"] else "default",
        ServiceName=state["inputs"]["tab3"].split("Microservice Name: ")[1].split("\n")[0] if "Microservice Name: " in state["inputs"]["tab3"] else "Default",
        context=context
    ) + (f"\nTab 2 Output:\n{state['outputs']['tab2']}" if "tab2" in state["outputs"] else "")
    response = llm.invoke(prompt).content
    state["outputs"]["tab3"] = response
    state["context"] = context
    return state

def boomi_node(state: TransformationState) -> TransformationState:
    if state["current_tab"] != "tab4":
        return state
    context = retrieve_context("Boomi APIM integration")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Generate an OpenAPI 3.0 YAML file and Boomi APIM instructions based on: {inputs}. Include:\n"
        "- `openapi.yaml`: OpenAPI spec with 2 endpoints (GET, POST), schemas, and Boomi policies (x-boomi-*).\n"
        "- `README.md`: Instructions for importing into Boomi APIM.\n"
        "Output each file prefixed with its path (e.g., `### openapi.yaml`).\n"
        "If Tab 3 output is available, use it to inform the design."
    ).format(inputs=state["inputs"]["tab4"] + (f"\nTab 3 Output:\n{state['outputs']['tab3']}" if "tab3" in state["outputs"] else ""), context=context)
    response = llm.invoke(prompt).content
    state["outputs"]["tab4"] = response
    state["context"] = context
    return state

def tests_node(state: TransformationState) -> TransformationState:
    if state["current_tab"] != "tab5":
        return state
    context = retrieve_context("JUnit testing for Spring Boot")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Generate JUnit 5 test cases for a Spring Boot microservice based on: {inputs}. Include:\n"
        "- `pom.xml`: Maven config with test dependencies (e.g., spring-boot-starter-test, mockito).\n"
        "- `src/test/java/com/example/{service_name}/controller/{ServiceName}ControllerTest.java`: Controller tests with @WebMvcTest.\n"
        "- `src/test/java/com/example/{service_name}/service/{ServiceName}ServiceTest.java`: Service tests with @SpringBootTest.\n"
        "Include at least 2 tests per class (success and failure). Output each file prefixed with its path (e.g., `### pom.xml`).\n"
        "If Tab 3 output is available, use it to inform the tests."
    ).format(
        inputs=state["inputs"]["tab5"],
        service_name=state["inputs"]["tab5"].split("Service Name: ")[1].split("\n")[0].lower() if "Service Name: " in state["inputs"]["tab5"] else "default",
        ServiceName=state["inputs"]["tab5"].split("Service Name: ")[1].split("\n")[0] if "Service Name: " in state["inputs"]["tab5"] else "Default",
        context=context
    ) + (f"\nTab 3 Output:\n{state['outputs']['tab3']}" if "tab3" in state["outputs"] else "")
    response = llm.invoke(prompt).content
    state["outputs"]["tab5"] = response
    state["context"] = context
    return state

def migrate_node(state: TransformationState) -> TransformationState:
    if state["current_tab"] != "tab6":
        return state
    context = retrieve_context("webMethods to Spring Boot migration")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Generate a migration plan and code to transform webMethods data and logic into a Spring Boot microservice based on: {inputs}. Include:\n"
        "- `migration.md`: Detailed step-by-step migration instructions.\n"
        "- `src/main/java/com/example/{service_name}/migration/{ServiceName}Migration.java`: Java class with migration code.\n"
        "Output each file prefixed with its path (e.g., `### migration.md`).\n"
        "If Tab 3 output is available, use it to inform the migration (e.g., align with generated entities)."
    ).format(
        inputs=state["inputs"]["tab6"],
        service_name=state["inputs"]["tab6"].split("Microservice Name: ")[1].split("\n")[0].lower() if "Microservice Name: " in state["inputs"]["tab6"] else "default",
        ServiceName=state["inputs"]["tab6"].split("Microservice Name: ")[1].split("\n")[0] if "Microservice Name: " in state["inputs"]["tab6"] else "Default",
        context=context
    ) + (f"\nTab 3 Output:\n{state['outputs']['tab3']}" if "tab3" in state["outputs"] else "")
    response = llm.invoke(prompt).content
    state["outputs"]["tab6"] = response
    state["context"] = context
    return state

def howto_node(state: TransformationState) -> TransformationState:
    if state["current_tab"] != "tab7":
        return state
    context = retrieve_context("webMethods to microservices transformation guide")
    prompt = PromptTemplate.from_template(
        "Using the following webMethods documentation context:\n{context}\n"
        "Generate a HowTo guide for transforming webMethods to microservices based on: {inputs}. Include:\n"
        "- Introduction: Overview of the process.\n"
        "- Step-by-Step Instructions: Detailed steps for analysis, design, code generation, API integration, testing, and migration.\n"
        "- Best Practices: Tips for success.\n"
        "Output as `### howto.md`.\n"
        "If outputs from Tabs 1-6 are available, consolidate them into the guide; otherwise, create a generic guide."
    ).format(inputs=state["inputs"]["tab7"], context=context)
    for tab in ["tab1", "tab2", "tab3", "tab4", "tab5", "tab6"]:
        if tab in state["outputs"]:
            prompt += f"\n{tab.upper()} Output:\n{state['outputs'][tab]}"
    response = llm.invoke(prompt).content
    state["outputs"]["tab7"] = response
    state["context"] = context
    return state

# Define graph
workflow = StateGraph(TransformationState)

# Add nodes
workflow.add_node("analyze", analyze_node)
workflow.add_node("design", design_node)
workflow.add_node("generate", generate_node)
workflow.add_node("boomi", boomi_node)
workflow.add_node("tests", tests_node)
workflow.add_node("migrate", migrate_node)
workflow.add_node("howto", howto_node)

# Define edges
workflow.add_edge("analyze", "design")
workflow.add_edge("design", "generate")
workflow.add_edge("generate", "boomi")
workflow.add_edge("boomi", "tests")
workflow.add_edge("tests", "migrate")
workflow.add_edge("migrate", "howto")
workflow.add_edge("howto", END)

# Set entry point
workflow.set_entry_point("analyze")

# Compile graph
graph = workflow.compile()

# Function to generate graph image (PNG only)
def generate_graph_image(current_tab: str) -> str:
    dot = "digraph G {\nrankdir=LR;\n"
    nodes = ["analyze", "design", "generate", "boomi", "tests", "migrate", "howto"]
    tab_map = {"tab1": "analyze", "tab2": "design", "tab3": "generate", "tab4": "boomi", "tab5": "tests", "tab6": "migrate", "tab7": "howto"}
    current_node = tab_map.get(current_tab, "analyze")

    for node in nodes:
        fillcolor = "green" if node == current_node else "lightblue"
        dot += f'{node} [label="{node.capitalize()} (Tab {nodes.index(node) + 1})", shape=box, style=filled, fillcolor={fillcolor}];\n'
    
    for i in range(len(nodes) - 1):
        dot += f"{nodes[i]} -> {nodes[i+1]};\n"
    dot += "}"

    # Generate image file
    graph_file = Source(dot, filename="workflow", format="png")
    graph_file.render(cleanup=True)
    return "workflow.png"

def run_agentic_workflow(inputs: Dict[str, Any], current_tab: str) -> Dict[str, str]:
    initial_state = {"inputs": inputs, "outputs": {}, "current_tab": current_tab, "context": ""}
    result = graph.invoke(initial_state)
    
    # Generate the graph image (PNG saved to disk)
    generate_graph_image(current_tab)
    return result["outputs"] 