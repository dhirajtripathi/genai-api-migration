from langchain_openai import AzureChatOpenAI
import os
from utils.rag_helper import retrieve_context, vectorstore
from langchain_google_genai import ChatGoogleGenerativeAI

def get_ai_response_az(prompt, use_rag=True):
    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        api_version="2023-05-15"
    )
    
    if use_rag:
        # Retrieve relevant context from webMethods docs
        context = retrieve_context(prompt, vectorstore, k=3)
        augmented_prompt = f"Context from webMethods documentation:\n{context}\n\nUser Prompt:\n{prompt}"
    else:
        augmented_prompt = prompt
    
    response = llm.invoke(augmented_prompt)
    return response.content

def get_ai_response(prompt, use_rag=True):
    G_API_KEY=os.getenv("Gemini_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash",api_key=G_API_KEY,temperature=0)
    
    if use_rag:
        # Retrieve relevant context from webMethods docs
        context = retrieve_context(prompt, vectorstore, k=3)
        augmented_prompt = f"Context from webMethods documentation:\n{context}\n\nUser Prompt:\n{prompt}"
    else:
        augmented_prompt = prompt
    
    response = llm.invoke(augmented_prompt)
    return response.content