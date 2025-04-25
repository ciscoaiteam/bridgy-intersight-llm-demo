from langchain_ollama import OllamaLLM  # Updated import
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from config import setup_langsmith

class GeneralExpert:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key = "LLM",
            model="/ai/models/Meta-Llama-3-8B-Instruct/", 
            base_url = "http://64.101.169.102:8000/v1",
            temperature=0.7
        )

        # Create prompt template
        self.prompt = ChatPromptTemplate.from_template("""
        You are a generalist. Use your broad knowledge to answer the question.

        Question: {question}

        Provide a detailed response:
        """)

        # Create chain using the new RunnableSequence pattern
        self.chain = self.prompt | self.llm

    def get_response(self, question: str) -> str:
        try:
            response = self.chain.invoke({"question": question})
            return response
        except Exception as e:
            raise Exception(f"General Expert error: {str(e)}")
