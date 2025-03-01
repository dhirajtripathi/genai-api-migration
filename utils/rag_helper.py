import os
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.vectorstores import FAISS
from pathlib import Path

# Initialize embeddings
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

# Persistent vector store path
VECTORSTORE_PATH = "vectorstore/faiss_index"

def initialize_vectorstore():
    """Initialize or load the FAISS vector store from webMethods PDFs."""
    if os.path.exists(VECTORSTORE_PATH):
        # Load existing vector store
        vectorstore = FAISS.load_local(VECTORSTORE_PATH, embeddings)
    else:
        # Load and process PDFs
        docs = []
        pdf_dir = "docs/"
        os.makedirs(pdf_dir, exist_ok=True)
        
        for pdf_file in Path(pdf_dir).glob("*.pdf"):
            loader = PyPDFLoader(str(pdf_file))
            docs.extend(loader.load())
        
        if not docs:
            raise ValueError("No PDF documents found in 'docs/' directory.")
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        
        # Create and save vector store
        vectorstore = FAISS.from_documents(splits, embeddings)
        vectorstore.save_local(VECTORSTORE_PATH)
    
    return vectorstore

def retrieve_context(query, vectorstore, k=3):
    """Retrieve relevant context from the vector store."""
    docs = vectorstore.similarity_search(query, k=k)
    return "\n".join([doc.page_content for doc in docs])

# Initialize vector store on module load
vectorstore = initialize_vectorstore()