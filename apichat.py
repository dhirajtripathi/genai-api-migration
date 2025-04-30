import os
import json
import streamlit as st
import hashlib
from dotenv import load_dotenv
from langchain.schema import Document
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
import concurrent.futures
import re
import zipfile
import io
from datetime import datetime

# ---- Load Environment Variables ----
load_dotenv()
GOOGLE_API_KEY =  os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

# ---- Configs ----
MAX_FILE_SIZE_MB = 2
MAX_DOCUMENTS = 10000  # Limit to prevent FAISS index bloat
INDEX_PATH = "index"
RETRIEVER_K = 5  # Broader context
CHUNK_OVERLAP = 100  # Better context preservation

# ---- Persona-Specific Prompts ----
PERSONA_PROMPTS = {
    "API Developer": """
You are an expert API Developer assisting with debugging and implementation. Your task is to analyze log and API metadata documents to identify errors, stack traces, and endpoint issues, considering the conversation history. Provide concise, technical answers with code snippets or log excerpts when relevant.

**Conversation History**:
{chat_history}

**Context**:
{context}

**Question**:
{question}

**Instructions**:
1. **Analyze**: Extract error messages, status codes, or stack traces from the context and history.
2. **Reason**: Infer causes of issues (e.g., timeout, connection refused) using technical details.
3. **Answer**: Provide a concise response with:
   - Bullet points for errors or issues.
   - Code snippets (e.g., curl commands) or log excerpts.
   - References to documents (e.g., "Based on log.txt").
4. **Fallback**: If no relevant information, respond: "No relevant debug information found. Try specifying [e.g., 'endpoint name', 'error type']."
5. Avoid non-technical speculation.

**Answer**:
""",
    "API Designer": """
You are an expert API Designer focused on creating and optimizing API specifications. Your task is to analyze log and API metadata documents to provide insights on API structure, request/response formats, and design best practices, considering the conversation history. Provide clear, design-focused answers with JSON examples when relevant.

**Conversation History**:
{chat_history}

**Context**:
{context}

**Question**:
{question}

**Instructions**:
1. **Analyze**: Identify API endpoints, payloads, or headers from the context and history.
2. **Reason**: Evaluate design quality (e.g., RESTful principles, error handling) and suggest improvements.
3. **Answer**: Provide a concise response with:
   - Bullet points for design observations or recommendations.
   - JSON examples for payloads or schemas.
   - References to documents (e.g., "Based on api.json").
4. **Fallback**: If no relevant information, respond: "No relevant design information found. Try specifying [e.g., 'endpoint details', 'payload structure']."
5. Avoid implementation-specific details unless requested.

**Answer**:
""",
    "API Architect": """
You are an expert API Architect focused on system-level design and scalability. Your task is to analyze log and API metadata documents to provide insights on architecture, performance, and security, considering the conversation history. Provide strategic, high-level answers with architectural recommendations when relevant.

**Conversation History**:
{chat_history}

**Context**:
{context}

**Question**:
{question}

**Instructions**:
1. **Analyze**: Extract performance metrics, security headers, or integration patterns from the context and history.
2. **Reason**: Assess scalability, reliability, or security risks and propose solutions.
3. **Answer**: Provide a concise response with:
   - Bullet points for architectural insights or recommendations.
   - Diagrams (in text, e.g., "Client -> API Gateway -> Service") if applicable.
   - References to documents (e.g., "Based on log.txt").
4. **Fallback**: If no relevant information, respond: "No relevant architectural information found. Try specifying [e.g., 'performance metrics', 'security headers']."
5. Avoid low-level implementation details unless requested.

**Answer**:
""",
    "QA": """
You are an expert QA Engineer focused on testing and validation. Your task is to analyze log and API metadata documents to identify defects, error conditions, and test scenarios, considering the conversation history. Provide actionable, test-focused answers with test case suggestions when relevant.

**Conversation History**:
{chat_history}

**Context**:
{context}

**Question**:
{question}

**Instructions**:
1. **Analyze**: Identify errors, edge cases, or inconsistent behaviors in the context and history.
2. **Reason**: Propose test cases to validate API behavior or uncover defects.
3. **Answer**: Provide a concise response with:
   - Bullet points for defects or test scenarios.
   - Test case tables (e.g., Input, Expected Output) if applicable.
   - References to documents (e.g., "Based on log.txt").
4. **Fallback**: If no relevant information, respond: "No relevant test information found. Try specifying [e.g., 'error conditions', 'test scenarios']."
5. Avoid design or implementation details unless requested.

**Answer**:
""",
    "BA": """
You are an expert Business Analyst focused on aligning APIs with business needs. Your task is to analyze log and API metadata documents to explain API functionality, map to business requirements, and identify gaps, considering the conversation history. Provide clear, business-oriented answers with use case descriptions when relevant.

**Conversation History**:
{chat_history}

**Context**:
{context}

**Question**:
{question}

**Instructions**:
1. **Analyze**: Identify API functionalities, endpoints, or data flows from the context and history.
2. **Reason**: Map these to business requirements and note any gaps or misalignments.
3. **Answer**: Provide a concise response with:
   - Bullet points for business functionalities or gaps.
   - Use case descriptions (e.g., "User retrieves order via /orders").
   - References to documents (e.g., "Based on api.json").
4. **Fallback**: If no relevant information, respond: "No relevant business information found. Try specifying [e.g., 'business use case', 'requirement details']."
5. Avoid technical implementation details unless requested.

**Answer**:
"""
}

# ---- Streamlit Config ----
st.set_page_config(page_title="GenAI Log & API Assistant", layout="wide")

# ---- Session State Init ----
if "qa_chain" not in st.session_state:
    st.session_state.qa_chain = None
if "docs" not in st.session_state:
    st.session_state.docs = []
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "selected_persona" not in st.session_state:
    st.session_state.selected_persona = "API Developer"  # Default persona

# ---- Header ----
st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px;">
        <img src="https://img.icons8.com/clouds/100/ai.png" width="60" />
        <h1 style="margin: 0;">GenAI Log & API Assistant</h1>
    </div>
    """, unsafe_allow_html=True)

# ---- Tabs (Main UI) ----
tab1, tab2, tab3 = st.tabs(["📁 Upload", "💬 Chat", "📚 Docs"])

# ---- File Parsers ----
def validate_json(content):
    """Validate JSON content."""
    try:
        json.loads(content)
        return True
    except json.JSONDecodeError:
        return False

def parse_json_file(file):
    """Parse a single JSON file."""
    if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        return None, f"File {file.name} is too large."
    try:
        content = file.read().decode("utf-8")
        if not validate_json(content):
            return None, f"Invalid JSON in {file.name}"
        data = json.loads(content)
        docs = []
        if isinstance(data, list):
            for item in data:
                docs.append(Document(page_content=json.dumps(item, indent=2), metadata={"source": file.name, "type": "json"}))
        else:
            docs.append(Document(page_content=json.dumps(data, indent=2), metadata={"source": file.name, "type": "json"}))
        return docs, None
    except Exception as e:
        return None, f"Error in {file.name}: {e}"

def parse_text_file(file):
    """Parse a single TXT file."""
    if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        return None, f"File {file.name} is too large."
    try:
        content = file.read().decode("utf-8")
        if not content.strip():
            return None, f"Empty content in {file.name}"
        return [Document(page_content=content, metadata={"source": file.name, "type": "txt"})], None
    except Exception as e:
        return None, f"Error in {file.name}: {e}"

def parse_log_file(file):
    """Parse a single LOG file, grouping multi-line entries with timestamp metadata."""
    if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        return None, f"File {file.name} is too large."
    try:
        content = file.read().decode("utf-8")
        if not content.strip():
            return None, f"Empty content in {file.name}"
        log_entry_pattern = r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}"
        entries = []
        current_entry = []
        timestamps = []
        for line in content.splitlines():
            if re.match(log_entry_pattern, line):
                if current_entry:
                    entries.append("".join(current_entry))
                    timestamps.append(current_entry[0].split()[0])
                current_entry = [line + "\n"]
            else:
                current_entry.append(line + "\n")
        if current_entry:
            entries.append("".join(current_entry))
            timestamps.append(current_entry[0].split()[0] if current_entry[0].strip() else "")
        docs = [
            Document(
                page_content=entry,
                metadata={"source": file.name, "type": "log", "timestamp": ts}
            ) for entry, ts in zip(entries, timestamps) if entry.strip()
        ]
        return docs, None
    except Exception as e:
        return None, f"Error in {file.name}: {e}"

def parse_uploaded_files(uploaded_files, parser_func):
    """Parse files in parallel using ThreadPoolExecutor."""
    docs = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(parser_func, uploaded_files)
        for result, error in results:
            if error:
                st.warning(error)
            elif result:
                docs.extend(result)
    return docs

# ---- Vector Store ----
def get_chunk_size(file_type):
    """Determine chunk size based on file type."""
    return 300 if file_type == "log" else 700

def build_vector_store(docs, save_path=INDEX_PATH):
    """Build FAISS vector store with dynamic chunking."""
    if len(docs) > MAX_DOCUMENTS:
        st.warning(f"Document limit exceeded. Indexing first {MAX_DOCUMENTS} documents.")
        docs = docs[:MAX_DOCUMENTS]
    
    embeddings = SentenceTransformerEmbeddings(model_name="all-distilroberta-v1")
    vs = None
    for doc in docs:
        file_type = doc.metadata["type"]
        chunk_size = get_chunk_size(file_type)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=CHUNK_OVERLAP)
        chunks = text_splitter.split_documents([doc])
        if vs is None:
            vs = FAISS.from_documents(chunks, embeddings)
        else:
            vs.add_documents(chunks)
    
    os.makedirs(save_path, exist_ok=True)
    vs.save_local(save_path)
    
    with open(os.path.join(save_path, "index.faiss"), "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
    with open(os.path.join(save_path, "checksum.txt"), "w") as f:
        f.write(checksum)
    
    return vs

def validate_faiss_index(load_path=INDEX_PATH):
    """Validate FAISS index using checksum."""
    try:
        with open(os.path.join(load_path, "index.faiss"), "rb") as f:
            current_checksum = hashlib.sha256(f.read()).hexdigest()
        with open(os.path.join(load_path, "checksum.txt"), "r") as f:
            stored_checksum = f.read().strip()
        return current_checksum == stored_checksum
    except Exception as e:
        st.error(f"Failed to validate FAISS index: {e}")
        return False

def load_vector_store(load_path=INDEX_PATH):
    """Load FAISS index with validation."""
    if not validate_faiss_index(load_path):
        raise ValueError("FAISS index validation failed. Rebuild the index.")
    embeddings = SentenceTransformerEmbeddings(model_name="all-distilroberta-v1")
    return FAISS.load_local(load_path, embeddings, allow_dangerous_deserialization=True)

# ---- Prompt Engineering ----
def get_qa_prompt(persona):
    """Get persona-specific prompt."""
    return PromptTemplate(
        template=PERSONA_PROMPTS[persona],
        input_variables=["chat_history", "context", "question"]
    )

def refine_query(query):
    """Simplify query refinement with rule-based logic."""
    query = query.lower().strip()
    if "error" in query and "list" not in query:
        return f"List error messages in the uploaded {query}"
    if "timeout" in query:
        return f"Identify causes of timeouts in the uploaded {query}"
    if "api" in query and "status" in query:
        return f"Show API status codes in the uploaded {query}"
    return query

def estimate_confidence(documents, query):
    """Estimate confidence based on document relevance."""
    if not documents:
        return 0.0
    query_terms = set(query.lower().split())
    relevant_docs = sum(
        1 for doc in documents
        if any(term in doc.page_content.lower() for term in query_terms)
    )
    return min(1.0, relevant_docs / RETRIEVER_K)

# ---- LLM Setup ----
def get_llm():
    """Get Google Gemini LLM."""
    return ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=GOOGLE_API_KEY, temperature=0.2)

def build_qa_chain(vector_store, persona):
    """Build ConversationalRetrievalChain with persona-specific prompt."""
    retriever = vector_store.as_retriever(search_kwargs={"k": RETRIEVER_K})
    llm = get_llm()
    return ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        combine_docs_chain_kwargs={"prompt": get_qa_prompt(persona)},
        return_source_documents=True
    )

# ---- Load Existing Vector Store ----
if os.path.exists(INDEX_PATH):
    try:
        st.session_state.vector_store = load_vector_store()
        st.session_state.qa_chain = build_qa_chain(st.session_state.vector_store, st.session_state.selected_persona)
    except Exception as e:
        st.error(f"Failed to load FAISS index: {e}. Please rebuild the assistant in the Upload tab.")

# ---- Tab 1: Upload ----
with tab1:
    st.subheader("📁 Upload Metadata & Logs")
    json_files = st.file_uploader("Upload JSON files", type=["json"], accept_multiple_files=True)
    txt_files = st.file_uploader("Upload TXT files", type=["txt"], accept_multiple_files=True)
    log_files = st.file_uploader("Upload LOG files (Splunk)", type=["log"], accept_multiple_files=True)

    if st.button("🚀 Build Assistant"):
        with st.spinner("Indexing documents..."):
            docs = (
                parse_uploaded_files(json_files, parse_json_file) +
                parse_uploaded_files(txt_files, parse_text_file) +
                parse_uploaded_files(log_files, parse_log_file)
            )
            if docs:
                st.session_state.vector_store = build_vector_store(docs)
                st.session_state.qa_chain = build_qa_chain(st.session_state.vector_store, st.session_state.selected_persona)
                st.session_state.docs = docs
                st.session_state.chat_history = []
                st.success("✅ Assistant is ready!")
            else:
                st.warning("⚠️ No valid documents found.")

    if os.path.exists(INDEX_PATH):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file in os.listdir(INDEX_PATH):
                zip_file.write(os.path.join(INDEX_PATH, file), file)
        buffer.seek(0)
        st.download_button("📥 Download FAISS Index", buffer, file_name="faiss_index.zip")

# ---- Tab 2: Chat ----
with tab2:
    st.subheader("💬 Conversational QA")
    
    # Persona selector
    st.session_state.selected_persona = st.selectbox(
        "Select Your Role",
        options=["API Developer", "API Designer", "API Architect", "QA", "BA"],
        index=["API Developer", "API Designer", "API Architect", "QA", "BA"].index(st.session_state.selected_persona)
    )
    
    # Rebuild QA chain if persona changes
    if st.session_state.vector_store:
        st.session_state.qa_chain = build_qa_chain(st.session_state.vector_store, st.session_state.selected_persona)
    
    # Clear chat history button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
    
    # Display chat history
    st.markdown("### Conversation History")
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            if isinstance(message, HumanMessage):
                st.markdown(
                    f"""
                    <div style='text-align: right; margin: 10px;'>
                        <div style='background-color: #DCF8C6; padding: 10px; border-radius: 10px; display: inline-block; max-width: 70%;'>
                            <b>You:</b> {message.content}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            elif isinstance(message, AIMessage):
                st.markdown(
                    f"""
                    <div style='text-align: left; margin: 10px;'>
                        <div style='background-color: #E6E6E6; padding: 10px; border-radius: 10px; display: inline-block; max-width: 70%;'>
                            <b>Assistant:</b> {message.content}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # Chat input form
    if st.session_state.qa_chain:
        with st.form(key="chat_form", clear_on_submit=True):
            question = st.text_input("Ask a question about your APIs or Logs:", key="chat_input")
            submit_button = st.form_submit_button("Send")
            
            if submit_button and question:
                with st.spinner("Thinking..."):
                    refined_question = refine_query(question)
                    history = []
                    for i in range(0, len(st.session_state.chat_history), 2):
                        if i + 1 < len(st.session_state.chat_history):
                            human_msg = st.session_state.chat_history[i].content
                            ai_msg = st.session_state.chat_history[i + 1].content
                            history.append((human_msg, ai_msg))
                    
                    result = st.session_state.qa_chain({
                        "question": refined_question,
                        "chat_history": history
                    })
                    
                    st.session_state.chat_history.append(HumanMessage(content=question))
                    st.session_state.chat_history.append(AIMessage(content=result["answer"]))
                    
                    st.markdown(f"**Refined Query:** {refined_question}")
                    st.markdown("### 🧠 Answer")
                    st.write(result["answer"])
                    
                    confidence = estimate_confidence(result["source_documents"], refined_question)
                    st.markdown(f"**Confidence Score:** {confidence:.2%}")
                    
                    st.markdown("### 🔍 Top Matching Documents")
                    for doc in result["source_documents"]:
                        st.markdown(f"**Source:** `{doc.metadata.get('source')}`")
                        with st.expander("View Full Content"):
                            st.code(doc.page_content)
    else:
        st.warning("Please upload files and build the assistant first in the Upload tab.")

# ---- Tab 3: Docs ----
with tab3:
    st.subheader("📚 Uploaded Documents")
    if st.session_state.docs:
        for doc in st.session_state.docs:
            st.markdown(f"**Source:** `{doc.metadata.get('source')}`")
            with st.expander("View Full Content"):
                st.code(doc.page_content)
    else:
        st.info("Upload files in the Upload tab to see them here.")
