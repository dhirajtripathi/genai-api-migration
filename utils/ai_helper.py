from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import os

def get_ai_response_az(prompt):
    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        api_version="2023-05-15"  # Adjust based on your Azure setup
    )
    response = llm.invoke(prompt)
    return response.content

def get_ai_response(prompt):
    G_API_KEY=os.getenv("Gemini_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash",api_key=G_API_KEY,temperature=0)
    response = llm.invoke(prompt)
    return response.content