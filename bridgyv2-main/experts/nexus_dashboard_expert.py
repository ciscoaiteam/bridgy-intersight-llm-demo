from langchain_ollama import OllamaLLM
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from tools.nexus_dashboard_api import NexusDashboardAPI
from config import setup_langsmith
import logging

logger = logging.getLogger(__name__)

class NexusDashboardExpert:
    def __init__(self):
        self.llm = OllamaLLM(
            model="gemma2",  # Using local gemma2 model
            base_url="http://localhost:11434",
            temperature=0.0
        )
        self.api = NexusDashboardAPI()

        # Create prompt template
        self.prompt = ChatPromptTemplate.from_template("""
        You are a Cisco Nexus Dashboard expert. You specialize in Cisco's data center networking solutions, 
        particularly the Nexus Dashboard platform which provides a centralized management interface for 
        Cisco's data center networking products.
        
        Use the API response data to answer the user's question accurately and professionally.
        If the API response contains an error, explain the issue and suggest troubleshooting steps.
        
        Question: {question}
        API Response: {api_response}

        Provide a detailed, technical, and helpful response. Include specific data from the API response
        when relevant, and explain networking concepts when appropriate. Format data in tables when it
        improves readability.
        """)

        # Create chain using the RunnableSequence pattern
        self.chain = self.prompt | self.llm

    def get_response(self, question: str) -> str:
        try:
            logger.info(f"Nexus Dashboard Expert processing question: {question}")
            api_response = self.api.query(question)
            
            if "Error:" in api_response and "initialization failed" in api_response:
                logger.error(f"Nexus Dashboard API initialization error: {api_response}")
                return self._handle_api_initialization_error(api_response)
                
            logger.debug(f"Nexus Dashboard API response received: {api_response[:100]}...")
            
            response = self.chain.invoke({
                "question": question,
                "api_response": api_response
            })
            
            return response
        except Exception as e:
            logger.error(f"Nexus Dashboard Expert error: {str(e)}")
            raise Exception(f"Nexus Dashboard Expert error: {str(e)}")
            
    def _handle_api_initialization_error(self, error_message: str) -> str:
        """Handle API initialization errors with a helpful message."""
        return (
            "I'm unable to connect to the Cisco Nexus Dashboard at this time. "
            "This could be due to one of the following reasons:\n\n"
            "1. The Nexus Dashboard credentials are not properly configured in the environment variables\n"
            "2. The Nexus Dashboard instance is not reachable from this server\n"
            "3. The Nexus Dashboard API is experiencing issues\n\n"
            "To resolve this issue, please check:\n"
            "- That the NEXUS_DASHBOARD_URL, NEXUS_DASHBOARD_USERNAME, and NEXUS_DASHBOARD_PASSWORD "
            "environment variables are correctly set\n"
            "- That the Nexus Dashboard instance is running and accessible\n"
            "- That the credentials provided have sufficient permissions\n\n"
            f"Technical details: {error_message}"
        )
