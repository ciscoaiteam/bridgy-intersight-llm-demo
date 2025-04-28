from __future__ import annotations

import os
import json
import logging
from typing import List, Dict, Any, Optional, Union

# Import existing API clients
from tools.intersight_api import IntersightAPI
from tools.nexus_dashboard_api import NexusDashboardAPI

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class InfrastructureAPI:
    """Tool for coordinating queries across multiple infrastructure APIs."""
    
    def __init__(self):
        """Initialize the Infrastructure API client."""
        try:
            # Initialize the individual API clients
            self.intersight_api = IntersightAPI()
            self.nexus_dashboard_api = NexusDashboardAPI()
            
            # Check if initialization of any API failed
            self.initialization_failed = False
            self.error_message = None
            
            if hasattr(self.intersight_api, 'initialization_failed') and self.intersight_api.initialization_failed:
                self.initialization_failed = True
                self.error_message = f"Intersight API initialization failed: {self.intersight_api.error_message}"
                logger.error(self.error_message)
            
            if hasattr(self.nexus_dashboard_api, 'initialization_failed') and self.nexus_dashboard_api.initialization_failed:
                if self.initialization_failed:
                    self.error_message += f"; Nexus Dashboard API initialization failed: {self.nexus_dashboard_api.error_message}"
                else:
                    self.initialization_failed = True
                    self.error_message = f"Nexus Dashboard API initialization failed: {self.nexus_dashboard_api.error_message}"
                logger.error(f"Nexus Dashboard API initialization failed: {self.nexus_dashboard_api.error_message}")
            
        except Exception as e:
            logger.error(f"Error initializing Infrastructure API: {str(e)}")
            self.initialization_failed = True
            self.error_message = str(e)
    
    def get_combined_switches_info(self) -> Dict[str, Any]:
        """Get combined switch information from both Intersight and Nexus Dashboard."""
        try:
            combined_switches = {
                "intersight_switches": [],
                "nexus_dashboard_switches": []
            }
            
            # Get switches from Intersight
            try:
                intersight_elements = self.intersight_api.client.get_network_elements()
                if not (isinstance(intersight_elements, dict) and "error" in intersight_elements):
                    combined_switches["intersight_switches"] = intersight_elements
                else:
                    logger.warning(f"Error getting Intersight network elements: {intersight_elements.get('error', 'Unknown error')}")
                    combined_switches["intersight_error"] = intersight_elements.get('error', 'Unknown error')
            except Exception as e:
                logger.error(f"Exception getting Intersight network elements: {str(e)}")
                combined_switches["intersight_error"] = str(e)
            
            # Get switches from Nexus Dashboard
            try:
                nexus_switches = self.nexus_dashboard_api.get_all_switches()
                if not (isinstance(nexus_switches, dict) and "error" in nexus_switches):
                    if "switches" in nexus_switches:
                        combined_switches["nexus_dashboard_switches"] = nexus_switches["switches"]
                    else:
                        combined_switches["nexus_dashboard_switches"] = nexus_switches
                else:
                    logger.warning(f"Error getting Nexus Dashboard switches: {nexus_switches.get('error', 'Unknown error')}")
                    combined_switches["nexus_dashboard_error"] = nexus_switches.get('error', 'Unknown error')
            except Exception as e:
                logger.error(f"Exception getting Nexus Dashboard switches: {str(e)}")
                combined_switches["nexus_dashboard_error"] = str(e)
            
            return combined_switches
            
        except Exception as e:
            logger.error(f"Error getting combined switches information: {str(e)}")
            return {"error": str(e)}
    
    def query(self, question: str) -> str:
        """Process a natural language query across multiple infrastructure systems."""
        if self.initialization_failed:
            return f"Error: Infrastructure API initialization failed. {self.error_message}"
        
        try:
            # Determine query type based on keywords
            question_lower = question.lower()
            
            # Check for switch-related queries
            if any(term in question_lower for term in ["switch", "switches", "network device", "network element"]):
                logger.info("Processing switch-related query")
                return self._format_switches_response(self.get_combined_switches_info())
            
            # For other queries, we could add more combined query handlers here
            # For now, just return a message about supported query types
            return "Please ask a question about switches or network devices in your environment. For other infrastructure queries, please use the specific expert (Intersight or Nexus Dashboard)."
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Error processing query: {str(e)}"
    
    def _format_switches_response(self, switches_info: Dict[str, Any]) -> str:
        """Format the combined switches information into a readable response."""
        if "error" in switches_info:
            return f"Error retrieving switch information: {switches_info['error']}"
        
        response = "### Switches in Your Environment\n\n"
        
        # Format Intersight switches
        if "intersight_switches" in switches_info and switches_info["intersight_switches"]:
            response += "## Intersight Network Elements\n\n"
            response += "| Device ID | Model | Serial | Management IP | Version |\n"
            response += "|-----------|-------|--------|---------------|----------|\n"
            
            for switch in switches_info["intersight_switches"]:
                device_id = switch.get('device_id', 'N/A')
                model = switch.get('model', 'N/A')
                serial = switch.get('serial', 'N/A')
                mgmt_ip = switch.get('management_ip', 'N/A')
                version = switch.get('version', 'N/A')
                
                response += f"| {device_id} | {model} | {serial} | {mgmt_ip} | {version} |\n"
        elif "intersight_error" in switches_info:
            response += "## Intersight Network Elements\n\n"
            response += f"Error retrieving Intersight network elements: {switches_info['intersight_error']}\n\n"
        else:
            response += "## Intersight Network Elements\n\n"
            response += "No network elements found in Intersight.\n\n"
        
        # Format Nexus Dashboard switches
        if "nexus_dashboard_switches" in switches_info and switches_info["nexus_dashboard_switches"]:
            response += "\n## Nexus Dashboard Switches\n\n"
            response += "| Device Name | IP Address | Serial Number | Model | Status | Fabric |\n"
            response += "|-------------|-----------|--------------|-------|--------|--------|\n"
            
            for switch in switches_info["nexus_dashboard_switches"]:
                device_name = switch.get('deviceName', 'N/A')
                ip_address = switch.get('ipAddress', 'N/A')
                serial = switch.get('serialNumber', 'N/A')
                model = switch.get('model', 'N/A')
                status = switch.get('status', 'N/A')
                fabric = switch.get('fabricName', 'N/A')
                
                response += f"| {device_name} | {ip_address} | {serial} | {model} | {status} | {fabric} |\n"
        elif "nexus_dashboard_error" in switches_info:
            response += "\n## Nexus Dashboard Switches\n\n"
            response += f"Error retrieving Nexus Dashboard switches: {switches_info['nexus_dashboard_error']}\n\n"
        else:
            response += "\n## Nexus Dashboard Switches\n\n"
            response += "No switches found in Nexus Dashboard.\n\n"
        
        return response
