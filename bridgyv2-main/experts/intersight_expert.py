from langchain_openai import ChatOpenAI  # Updated import
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

        Provide a detailed and technical response:
        """)

        # Create chain using the new RunnableSequence pattern
        self.chain = self.prompt | self.llm

    def get_response(self, question: str) -> str:
        try:
            api_response = self.api.query(question)
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
