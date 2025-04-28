from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, List, Optional

from langchain_openai import ChatOpenAI
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
                api_key="LLM",
                model="/ai/models/Meta-Llama-3-8B-Instruct/",
                base_url="http://64.101.169.102:8000/v1",
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
            
            # Get the LLM response
            response = self.llm([
                SystemMessage(content=prompt),
                HumanMessage(content=question)
            ])
            
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
            logger.error(f"Error processing query: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Error processing infrastructure query: {str(e)}"
    
    def _create_prompt(self, query: str, api_response: str) -> str:
        """Create a prompt for the LLM based on the query and API response."""
        prompt = """
        You are a Cisco Infrastructure expert. Use your knowledge and the API response to answer the question.

        Question: {query}
        API Response: {api_response}

        IMPORTANT GUIDELINES:
        1. If the API response contains a formatted table or list, present this information directly without additional analysis.
        2. For switch-specific queries, focus on the information listed in the API response.
        3. If the API response contains both Intersight and Nexus Dashboard data, include information from both sources.
        4. Maintain the structure in your response, such as separating Intersight and Nexus Dashboard information.
        5. Provide factual information based on the API response rather than speculative analysis.

        Provide a detailed and technical response:
        """
        
        # Format the prompt with the query and API response
        formatted_prompt = prompt.format(query=query, api_response=api_response)
        
        return formatted_prompt
