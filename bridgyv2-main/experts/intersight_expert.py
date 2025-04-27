from langchain_ollama import OllamaLLM  # Updated import
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from tools.intersight_api import IntersightAPI
from config import setup_langsmith
import re
import logging

logger = logging.getLogger(__name__)

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
            
            # Extract server name for firmware queries
            server_name = None
            if is_firmware_query and "server" in question.lower():
                # Look for patterns like "for server X" or "server X"
                server_patterns = [
                    r"(?:for|on)\s+server\s+([a-zA-Z0-9_\-]+)",  # "for server xyz"
                    r"server\s+([a-zA-Z0-9_\-]+)\s+(?:what|which)",  # "server xyz what"
                    r"(?:update|upgrade)\s+([a-zA-Z0-9_\-]+)\s+to",  # "update xyz to"
                    r"server\s+([a-zA-Z0-9_\-]+)",  # Just "server xyz" anywhere in the query
                ]
                
                for pattern in server_patterns:
                    match = re.search(pattern, question.lower())
                    if match:
                        server_name = match.group(1)
                        logger.info(f"Matched server name '{server_name}' using pattern: {pattern}")
                        break
                
                # If we couldn't find a server name but the query contains "server" and is about firmware,
                # look for any word that might be a server name (alphanumeric with possible hyphens)
                if not server_name:
                    words = question.lower().split()
                    for i, word in enumerate(words):
                        if i > 0 and words[i-1] == "server" and re.match(r'^[a-z0-9_\-]+$', word):
                            server_name = word
                            logger.info(f"Found server name '{server_name}' by word position after 'server'")
                            break
            
            # For server-specific firmware queries, directly call the firmware method
            if is_firmware_query and server_name:
                logger.info(f"Directly handling firmware query for server: {server_name}")
                try:
                    # Get firmware information directly
                    if hasattr(self.api.client, 'get_firmware_for_server'):
                        firmware_info = self.api.client.get_firmware_for_server(server_name)
                        if isinstance(firmware_info, dict) and "error" not in firmware_info:
                            # Format the response
                            api_response = self._format_firmware_response(firmware_info)
                            logger.info(f"Generated firmware response for {server_name}")
                            return api_response
                except Exception as firmware_error:
                    logger.error(f"Error getting firmware directly: {str(firmware_error)}")
                    # Continue with normal flow if direct method fails
            
            # Get API response through the normal query method
            api_response = self.api.query(question)
            
            # For firmware queries, check if we got a proper response with firmware details
            if is_firmware_query and server_name and "## Available Firmware Updates for" in api_response:
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
            logger.error(f"Intersight Expert error: {str(e)}")
            raise Exception(f"Intersight Expert error: {str(e)}")
            
    def _format_firmware_response(self, firmware_info: dict) -> str:
        """Format firmware information into a readable response."""
        server_name = firmware_info.get("server_name", "N/A")
        server_model = firmware_info.get("server_model", "N/A")
        current_firmware = firmware_info.get("current_firmware", "Unknown")
        compatible_firmware = firmware_info.get("compatible_firmware", [])
        
        if not compatible_firmware:
            return f"## Available Firmware Updates for {server_name}\n\n" + \
                   f"**Server Model:** {server_model}\n" + \
                   f"**Current Firmware:** {current_firmware}\n\n" + \
                   "No compatible firmware updates were found for this server model."
        
        response = f"## Available Firmware Updates for {server_name}\n\n"
        response += f"**Server Model:** {server_model}\n"
        response += f"**Current Firmware:** {current_firmware}\n\n"
        
        response += "### Compatible Firmware Packages\n\n"
        response += "| Firmware Name | Version | Bundle Type | Platform |\n"
        response += "|--------------|---------|-------------|----------|\n"
        
        for firmware in compatible_firmware:
            response += f"| {firmware.get('name', 'N/A')} | {firmware.get('version', 'N/A')} | {firmware.get('bundle_type', 'N/A')} | {firmware.get('platform_type', 'N/A')} |\n"
        
        return response
