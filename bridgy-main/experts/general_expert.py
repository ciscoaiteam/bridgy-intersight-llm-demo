from requests import api
from langchain_ollama import OllamaLLM  # Updated import
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from config import setup_langsmith
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class GeneralExpert:
    def __init__(self):
        self.llm = OllamaLLM(
            model="gemma2",  # Using local gemma2al model
            base_url="http://localhost:11434",
            temperature=0.0
        )

        # Create prompt template
        self.prompt = ChatPromptTemplate.from_template("""
        You are a generalist. Use your broad knowledge to answer the question.

        Question: {question}

        FORMAT INSTRUCTIONS:
        Format your response in HTML instead of Markdown. Use appropriate HTML tags like:
        - <h4> for headings
        - <p> for paragraphs
        - <ul>, <ol>, <li> for lists
        - <code> for code snippets
        - <b>, <i>, <u> for text formatting
        - <table>, <tr>, <th>, <td> for tables
        - <a href="URL">link text</a> for links
        
        Provide a detailed response formatted in HTML:
        """)

        # Create chain using the new RunnableSequence pattern
        self.chain = self.prompt | self.llm

    def get_response(self, question: str) -> str:
        try:
            response = self.chain.invoke({"question": question})
            
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
            raise Exception(f"General Expert error: {str(e)}")
