from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, List, Optional

from langchain_openai import ChatOpenAI
# Using OpenAI-compatible API for remote LLM or vLLM
from langchain.schema.messages import HumanMessage, SystemMessage

from tools.infrastructure_api import InfrastructureAPI

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class InfrastructureExpert:
    """Expert for handling infrastructure queries across multiple systems."""
    
    def __init__(self):
        """Initialize the Infrastructure Expert."""
        try:
            # Initialize the infrastructure API
            self.api = InfrastructureAPI()
            
            # Initialize the LLM
            self.llm = ChatOpenAI(
                model_name=os.getenv("LLM_MODEL", "gemma-2-9b"),
                base_url=os.getenv("LLM_SERVICE_URL", "http://vllm-server:8000/v1"),
                api_key=os.getenv("LLM_API_KEY", "llm-api-key"),
                temperature=0.0
            )
            
        except Exception as e:
            logger.error(f"Error initializing Infrastructure Expert: {str(e)}")
            raise
    
    def get_response(self, question: str) -> str:
        """Process a query related to infrastructure."""
        try:
            # Get the API response
            api_response = self.api.query(question)
            
            # Create a prompt for the LLM
            prompt = self._create_prompt(question, api_response)
            
            # Get the LLM response - use invoke() method with a string prompt
            response = self.llm.invoke(prompt + "\n\n" + question)
            
            # Return the response string
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Error processing infrastructure query: {str(e)}"
    
    def _create_prompt(self, question: str, api_response: str) -> str:
        """Create a prompt for the LLM."""
        return f"""
        You are a Cisco Infrastructure expert specializing in data from multiple systems. 
        Format your response to clearly separate information from different sources.
        
        API Response Data:
        {api_response}
        
        FORMAT INSTRUCTIONS:
        Format your response in HTML instead of Markdown. Use appropriate HTML tags like:
        - <h4> for headings
        - <p> for paragraphs
        - <ul>, <ol>, <li> for lists
        - <code> for code snippets
        - <b>, <i>, <u> for text formatting
        - <table>, <tr>, <th>, <td> for tables with proper structure
        - <a href=\"URL\">link text</a> for links
        
        SPECIAL FORMATTING FOR SPECIFIC QUERIES:
        1. For fabric-related questions ("What fabrics are in my environment?"), use the following format:
           <h4>Fabrics in Your Environment</h4>
           <p>There are [number] fabric(s) in your environment.</p>
           
           <h4>Fabric Details</h4>
           [Fabric information in table or list format]

        2. For switch-related questions ("What switches are in my environment?"), ALWAYS include information from BOTH Intersight and Nexus Dashboard sources if available in the API response. Show both sections even if one has no switches.
           <h4>Switches in Your Environment</h4>
           <h5>Intersight Network Elements</h5>
           [Intersight switch details in table format]
           
           <h5>Nexus Dashboard Switches</h5>
           [Nexus Dashboard switch details in table format]
        
        GLOBAL RULES FOR ALL RESPONSES:
        1. NEVER mention API response data in your answer
        2. Get straight to the point with direct, concise answers
        3. Use <h4> for section headers within responses
        4. If information is available from multiple sources, ALWAYS include ALL sources available in the API response
        5. For switch information, you MUST include data from BOTH Intersight and Nexus Dashboard sources
        
        Be technical, concise, and factual. Format your entire response in HTML.
        """
