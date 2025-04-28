from langchain_ollama import OllamaLLM  # Updated import
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from tools.pdf_loader import PDFLoader
from config import setup_langsmith
import logging

logger = logging.getLogger(__name__)

class AIPodExpert:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key = "LLM",
            model="/ai/models/Meta-Llama-3-8B-Instruct/", 
            base_url = "http://64.101.169.102:8000/v1",
            temperature=0.0
        )
        self.pdf_loader = PDFLoader()

        # Create prompt template
        self.prompt = ChatPromptTemplate.from_template("""
        You are a Cisco AI Pods expert. Use the provided documentation context to answer the question accurately.

        When responding about AI Pods, focus on:
        - Hardware specifications and requirements for different LLM sizes
        - Appropriate AI Pod configurations for specific workloads
        - Deployment and operational best practices
        - Performance characteristics and scaling guidelines

        If the question asks about specific LLM sizes (like 40B models), provide detailed hardware recommendations.

        Question: {question}
        Documentation Context: {context}

        IMPORTANT: For each claim or technical detail in your response, include a reference to the specific part of the documentation where this information was found. Use a format like: "[Reference: Page X of AI Infrastructure Pods document]" or similar appropriate citation.

        At the end of your response, include a "Sources" section that lists all the documentation references you used.

        Provide a detailed and technical response based on the actual documentation:
        """)

        # Create chain using the new RunnableSequence pattern
        self.chain = self.prompt | self.llm

    def get_response(self, question: str) -> str:
        try:
            # Get relevant context from PDF documents
            context = self.pdf_loader.get_relevant_context(question)
            
            # Create the prompt with context
            prompt_with_context = self.prompt.format(
                question=question,
                context=context
            )
            
            # Generate response
            response = self.chain.invoke({
                "question": question,
                "context": context
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
            raise Exception(f"AI Pods Expert error: {str(e)}")
