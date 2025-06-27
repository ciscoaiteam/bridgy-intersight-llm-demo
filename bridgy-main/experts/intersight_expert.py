from langchain_ollama import OllamaLLM  # Updated import
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from tools.intersight_api import IntersightAPI
from config import setup_langsmith
import re
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class IntersightExpert:
    def __init__(self):
        self.llm = OllamaLLM(
            model="gemma2",  # Using local gemma2al model
            base_url="http://localhost:11434",
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

        FORMAT INSTRUCTIONS:
        Format your response in HTML instead of Markdown. Use appropriate HTML tags like:
        - <h4> for headings
        - <p> for paragraphs
        - <ul>, <ol>, <li> for lists
        - <code> for code snippets
        - <b>, <i>, <u> for text formatting
        - <table>, <tr>, <th>, <td> for tables with proper structure
        - <a href="URL">link text</a> for links
        
        For tables, use the following structure:
        <table>
          <tr>
            <th>Header 1</th>
            <th>Header 2</th>
          </tr>
          <tr>
            <td>Data 1</td>
            <td>Data 2</td>
          </tr>
        </table>

        Provide a detailed and technical response formatted in HTML:
        """)

        # Create chain using the new RunnableSequence pattern
        self.chain = self.prompt | self.llm

    def get_response(self, question: str) -> str:
        try:
            # First check if this is a GPU-related query - this takes priority
            is_gpu_query = any(term in question.lower() for term in ["gpu", "graphics card", "nvidia", "amd", "video card", "accelerator", "cuda", "graphics processing", "gpus", "graphics cards"])
            if is_gpu_query:
                logger.info(f"Detected GPU query: {question}")
                # Process GPU query immediately
                try:
                    # Get GPU information directly
                    if hasattr(self.api.client, 'get_server_gpus'):
                        gpu_servers = self.api.client.get_server_gpus()
                        if isinstance(gpu_servers, list) and gpu_servers:
                            # Format GPU information into a readable response
                            if hasattr(self.api, '_format_gpu_response'):
                                api_response = self.api._format_gpu_response(gpu_servers)
                                logger.info(f"Generated GPU response using API formatter")
                                return api_response
                            
                    # If we get here, something went wrong with GPU processing
                    logger.error("Could not process GPU query directly, falling back to general handling")
                except Exception as gpu_error:
                    logger.error(f"Error in initial GPU query processing: {str(gpu_error)}")
            
            # Then check if this is a firmware-related query
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
            
            # Check for server inventory queries
            is_server_inventory_query = any(pattern in question.lower() for pattern in [
                "what servers", "server inventory", "list of servers", 
                "servers in my", "my servers", "all servers", "servers are", "servers running", 
                "running servers", "what servers are", "what are the servers", "show me the servers", "environment"
            ]) and not ("firmware" in question.lower() and any(term in question.lower() for term in ["upgrade", "update", "can be upgraded"])) and not is_gpu_query
            
            # For server inventory queries, directly handle them
            if is_server_inventory_query:
                logger.info(f"Directly handling server inventory query")
                try:
                    server_data = self.api.client.get_servers()
                    if isinstance(server_data, list) and server_data:
                        api_response = self.api._format_servers_response(server_data)
                        logger.info(f"Generated server inventory response")
                        return api_response
                except Exception as server_error:
                    logger.error(f"Error getting server inventory directly: {str(server_error)}")
                    # Continue with normal flow if direct method fails
                    
            # GPU queries are already handled at the beginning of the function
            # No need to check for them again here
            
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
            logger.error(f"Error in IntersightExpert: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Error processing your request: {str(e)}"

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
        
    def _format_gpu_response(self, gpu_servers: list) -> str:
        """Format GPU information from servers into a readable response."""
        if not gpu_servers:
            return "## GPUs in Environment\n\nNo servers with GPUs were found in your environment."
        
        response = "## GPUs in Environment\n\n"
        response += "The following GPUs are running in your environment:\n\n"
        response += "| Server Name | Server Model | GPU Model |\n"
        response += "|-------------|-------------|-----------|\n"
        
        gpu_count = 0
        for server in gpu_servers:
            server_name = server.get("name", "N/A")
            server_model = server.get("model", "N/A")
            
            gpus = server.get("gpus", [])
            if not gpus:
                continue
                
            for gpu in gpus:
                gpu_count += 1
                gpu_model = gpu.get("model", "N/A")
                # Remove memory and status from output
                
                response += f"| {server_name} | {server_model} | {gpu_model} |\n"
        
        if gpu_count == 0:
            response = "## GPUs in Environment\n\nNo GPUs were detected in any of your servers."
            
        return response
