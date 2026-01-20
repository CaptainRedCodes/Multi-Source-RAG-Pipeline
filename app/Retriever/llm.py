import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)

from langchain.messages import SystemMessage

from app.Retriever.rag_retriever import RAGRetriever

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class LLM:
    def __init__(self,rag:RAGRetriever,model_name:str="meta-llama/llama-4-maverick-17b-128e-instruct"):
        self.model_name = model_name
        self.api_keys = GROQ_API_KEY
        self.rag = rag
        if not self.api_keys:
            raise ValueError("API Key Not Found")
        
        self.llm=ChatGroq(
            model = self.model_name,
            temperature=0.3,
            max_tokens=2048,
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
   
             SystemMessage(
                    content="You are a helpful AI assistant. Answer ONLY using the provided context."
            ),
            HumanMessagePromptTemplate.from_template(
                    "Context:\n{context}\n\nQuestion:\n{question}"
             )
        ])

    def generate_response(self,query:str,context:str,max_length:int = 500)->str:
        try:
            messages = self.prompt.format_messages(
                question=query,
                context=context
            )

            response = self.llm.invoke(messages)
            print("Generating LLM Response from query and context")
            return str(response.content)

        except Exception as e:
            return f"Error generating response: {e}"

    def llm_rag_retrive(self,query:str,top_k=2):
        result = self.rag.retrieve(query,top_k)
        context = "\n\n".join([doc['content'] for doc in result]) if result else ""

        if not context:
            return "No Answer"
        
        response = self.generate_response(
            query=query,
            context=context
        )

        return response

