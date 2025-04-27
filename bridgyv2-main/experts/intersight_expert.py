from langchain_ollama import OllamaLLM  # Updated import
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from tools.intersight_api import IntersightAPI
from config import setup_langsmith

class IntersightExpert:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key = "LLM",
            model="/ai/models/Meta-Llama-3-8B-Instruct/", 
            base_url = "http://64.101.169.102:8000/v1",
            temperature=0.0
        )
        self.api = IntersightAPI()

        # Create prompt template
        self.prompt = ChatPromptTemplate.from_template("""
        You are a Cisco Intersight infrastructure expert. Use your knowledge and the API response to answer the question.

        Question: {question}
        API Response: {api_response}

        IMPORTANT GUIDELINES:
        1. If the API response contains a formatted table or list of firmware updates, present this information directly without additional analysis.
        2. For server-specific firmware queries, focus on the compatible firmware packages listed in the API response.
        3. Do not compare servers with different models unless specifically asked.
        4. If the API response contains "Available Firmware Updates for [server]" or similar headings, maintain this structure in your response.
        5. Provide factual information based on the API response rather than speculative analysis.

        Provide a detailed and technical response:
        """)

        # Create chain using the new RunnableSequence pattern
        self.chain = self.prompt | self.llm

    def get_response(self, question: str) -> str:
        try:
            # Check if this is a firmware-related query for a specific server
            is_firmware_query = any(term in question.lower() for term in ["firmware", "update", "upgrade"])
            is_server_specific = "server" in question.lower() and any(char.isalnum() for char in question)
            
            # Get API response
            api_response = self.api.query(question)
            
            # For firmware queries, check if we got a proper response with firmware details
            if is_firmware_query and is_server_specific and "## Available Firmware Updates for" in api_response:
                # If we have a well-formatted firmware response, return it directly
                return api_response
            
            # Otherwise, use the LLM to interpret the response
            response = self.chain.invoke({
                "question": question,
                "api_response": api_response
            })
            
            # Extract just the content from the response
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, dict) and 'content' in response:
                return response['content']
            elif isinstance(response, str):
                return response
            else:
                # Try to convert the response to a string if it's not already
                return str(response)
                
        except Exception as e:
            raise Exception(f"Intersight Expert error: {str(e)}")
