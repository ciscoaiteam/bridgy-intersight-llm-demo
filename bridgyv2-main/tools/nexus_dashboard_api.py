from __future__ import annotations

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
import time
from urllib3.exceptions import InsecureRequestWarning
import urllib3
from dotenv import load_dotenv

# Suppress insecure request warnings
urllib3.disable_warnings(InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class NexusDashboardAPI:
    """Tool for interacting with Cisco Nexus Dashboard API."""
    
    def __init__(self):
        """Initialize the Nexus Dashboard API client."""
        try:
            # Ensure environment variables are loaded
            load_dotenv()
            
            # Get API credentials from environment variables
            self.base_url = os.getenv("NEXUS_DASHBOARD_URL", "").rstrip('/')
            self.username = os.getenv("NEXUS_DASHBOARD_USERNAME")
            self.password = os.getenv("NEXUS_DASHBOARD_PASSWORD")
            self.domain = os.getenv("NEXUS_DASHBOARD_DOMAIN", "local")
            
            logger.debug(f"Environment variables loaded: URL={bool(self.base_url)}, Username={bool(self.username)}, Password={bool(self.password)}")
            
            if not self.base_url or not self.username or not self.password:
                missing_vars = []
                if not self.base_url:
                    missing_vars.append("NEXUS_DASHBOARD_URL")
                if not self.username:
                    missing_vars.append("NEXUS_DASHBOARD_USERNAME")
                if not self.password:
                    missing_vars.append("NEXUS_DASHBOARD_PASSWORD")
                    
                error_msg = f"Nexus Dashboard credentials not found in environment variables: {', '.join(missing_vars)}"
                logger.error(error_msg)
                self.initialization_failed = True
                self.error_message = error_msg
                return
                
            logger.debug(f"Nexus Dashboard URL: {self.base_url}")
            logger.debug(f"Nexus Dashboard Username: {self.username}")
            
            # Initialize session
            self.session = requests.Session()
            self.session.verify = False  # Skip SSL verification
            
            # Set default headers
            self.session.headers.update({
                "Content-Type": "application/json",
                "Accept": "application/json"
            })
            
            # Initialize API endpoints based on Nexus Dashboard API documentation
            self.initialize_endpoints()
            
            # Authenticate and get JWT token
            self.jwt_token = None
            login_result = self.login()
            
            if not login_result:
                self.initialization_failed = True
                self.error_message = "Failed to authenticate with Nexus Dashboard"
                return
                
            self.initialization_failed = False
            self.error_message = None
            
        except Exception as e:
            logger.error(f"Error initializing Nexus Dashboard API: {str(e)}")
            self.initialization_failed = True
            self.error_message = str(e)
    
    def initialize_endpoints(self):
        """Initialize API endpoints based on Nexus Dashboard API documentation."""
        # Based on the Nexus Dashboard API documentation v3.2.1
        self.endpoints = {
            # Authentication endpoints
            "login": "/login",
            "logout": "/logout",
            
            # Site Management
            "fabrics": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics",
        }
        
        logger.debug("API endpoints initialized")
    
    def login(self):
        """Authenticate with Nexus Dashboard and get JWT token."""
        try:
            login_url = f"{self.base_url}{self.endpoints['login']}"
            logger.debug(f"Authenticating to Nexus Dashboard at {login_url}")
            
            # Validate URL format
            if not self.base_url.startswith(('http://', 'https://')):
                logger.error(f"Invalid URL format: {self.base_url}")
                return False
                
            login_data = {
                "userName": self.username,
                "userPasswd": self.password,
                "domain": self.domain
            }
            
            logger.debug(f"Login attempt with username: {self.username}, domain: {self.domain}")
            
            try:
                response = self.session.post(
                    url=login_url,
                    json=login_data,
                    timeout=30,
                    verify=False  # Disable SSL verification for self-signed certificates
                )
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error: {str(e)}")
                self.error_message = f"Connection error: Could not connect to {self.base_url}. Please verify the URL is correct and the server is accessible."
                return False
            
            if response.status_code != 200:
                logger.error(f"Authentication failed with status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                self.error_message = f"Authentication failed with status code: {response.status_code}. Response: {response.text[:200]}"
                return False
            
            # Parse the response to get the JWT token
            try:
                response_data = response.json()
                
                # The token might be in 'token' or 'jwttoken' field
                self.jwt_token = response_data.get('token') or response_data.get('jwttoken')
                
                if not self.jwt_token:
                    logger.error("JWT token not found in login response")
                    logger.debug(f"Response data: {json.dumps(response_data)}")
                    self.error_message = "JWT token not found in login response"
                    return False
                
                # Update session headers with JWT token
                self.session.headers.update({
                    "Authorization": f"Bearer {self.jwt_token}"
                })
                
                logger.debug("Successfully authenticated with Nexus Dashboard")
                return True
                
            except json.JSONDecodeError:
                logger.error("Failed to parse login response as JSON")
                logger.error(f"Response text: {response.text}")
                self.error_message = f"Failed to parse login response as JSON: {response.text[:200]}"
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during authentication: {str(e)}")
            self.error_message = f"Network error during authentication: {str(e)}"
            return False
            
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            self.error_message = f"Error during authentication: {str(e)}"
            return False

    def _make_request(self, method, endpoint, params=None, data=None):
        """Make an API request with authentication."""
        try:
            # Check if we have a valid JWT token
            if not self.jwt_token:
                logger.debug("No JWT token available, attempting to login")
                if not self.login():
                    return {"error": f"Failed to authenticate with Nexus Dashboard: {self.error_message}"}
            
            # Ensure endpoint starts with a slash
            if not endpoint.startswith('/'):
                endpoint = '/' + endpoint
                
            url = f"{self.base_url}{endpoint}"
            logger.debug(f"Making {method} request to {url}")
            
            if params:
                logger.debug(f"Request params: {params}")
            if data:
                logger.debug(f"Request data: {json.dumps(data)[:200]}")  # Log first 200 chars
            
            try:    
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    timeout=30  # Set a reasonable timeout
                )
                
                logger.debug(f"Response status code: {response.status_code}")
                
                # If we get a 401, our token might have expired, try to login again
                if response.status_code == 401:
                    logger.debug("Received 401 Unauthorized, attempting to re-authenticate")
                    if self.login():
                        # Retry the request with the new token
                        response = self.session.request(
                            method=method,
                            url=url,
                            params=params,
                            json=data,
                            timeout=30
                        )
                        logger.debug(f"Retry response status code: {response.status_code}")
                
                # Check for HTTP errors
                if response.status_code >= 400:
                    logger.error(f"HTTP error: {response.status_code}")
                    logger.error(f"Response content: {response.text}")  # Log full response for debugging
                    return {
                        "error": f"HTTP error {response.status_code}",
                        "message": response.text[:500] if response.text else "No response content",
                        "status_code": response.status_code
                    }
                    
                # Try to parse JSON response
                try:
                    response_data = response.json()
                    logger.debug(f"Successfully parsed response as JSON")
                    return response_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse response as JSON: {str(e)}")
                    # If response is not JSON, return the text content
                    return {
                        "content": response.text[:1000],  # Limit to 1000 chars
                        "content_type": response.headers.get('Content-Type', 'unknown')
                    }
            
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error: {str(e)}")
                return {"error": f"Connection error: Could not connect to {url}. Please verify the URL is correct and the server is accessible."}
                
            except requests.exceptions.Timeout as e:
                logger.error(f"Request timed out: {str(e)}")
                return {"error": f"Request timed out after 30 seconds: {str(e)}"}
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {str(e)}")
            if e.response.status_code == 401:
                # API key might be invalid
                logger.error("Received 401 Unauthorized, API key may be invalid")
                return {"error": "API key authentication failed", "status_code": e.response.status_code}
            return {"error": str(e), "status_code": e.response.status_code}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during request: {str(e)}")
            return {"error": f"Network error: {str(e)}"}
            
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return {"error": str(e)}
    

    

    
    def get_fabrics(self):
        """Get list of fabrics from Nexus Dashboard."""
        # Try GET first
        result = self._make_request("GET", self.endpoints["fabrics"])
        
        # Debug log the result type and structure
        if isinstance(result, list):
            logger.debug(f"Received list response with {len(result)} items")
            if len(result) > 0:
                logger.debug(f"First item sample: {str(result[0])[:100]}...")
        elif isinstance(result, dict):
            logger.debug(f"Received dict response with keys: {result.keys()}")
        else:
            logger.debug(f"Received response of type: {type(result)}")
        
        # If GET fails, try POST with empty data
        if isinstance(result, dict) and result.get("error"):
            logger.debug("GET fabrics endpoint failed, trying POST")
            result = self._make_request("POST", self.endpoints["fabrics"], data={})
        
        return result
    


    
    def query(self, question: str) -> str:
        """Process a natural language query about Nexus Dashboard."""
        if self.initialization_failed:
            return f"Error: Nexus Dashboard API initialization failed. {self.error_message}"
        
        try:
            # Process the question to determine what data to fetch
            question_lower = question.lower()
            
            response_data = {}
            
            if any(term in question_lower for term in ["fabric", "fabrics", "network fabric"]):
                logger.debug("Querying fabrics information")
                fabrics_result = self.get_fabrics()
                
                # Handle different response types
                if isinstance(fabrics_result, list):
                    logger.debug(f"Processing list response with {len(fabrics_result)} items")
                    # If it's a list, it's likely a list of fabrics
                    # Extract only essential information to reduce response size
                    simplified_fabrics = []
                    for fabric in fabrics_result:
                        if isinstance(fabric, dict):
                            simplified_fabric = {
                                "fabricId": fabric.get("fabricId", "Unknown"),
                                "fabricName": fabric.get("fabricName", "Unknown"),
                                "fabricType": fabric.get("fabricType", "Unknown"),
                                "fabricState": fabric.get("fabricState", "Unknown")
                            }
                            simplified_fabrics.append(simplified_fabric)
                        else:
                            simplified_fabrics.append(str(fabric))
                    
                    response_data["fabrics"] = {
                        "count": len(fabrics_result),
                        "items": simplified_fabrics
                    }
                elif isinstance(fabrics_result, dict):
                    logger.debug(f"Processing dictionary response")
                    # If it's a dictionary, it might contain error information or structured data
                    response_data["fabrics"] = fabrics_result
                else:
                    logger.debug(f"Processing response of type {type(fabrics_result)}")
                    # For any other type, convert to string
                    response_data["fabrics"] = {
                        "data": str(fabrics_result)
                    }
            
            # Check if the question is about external IP configuration for trap and syslog
            if any(term in question_lower for term in ["external ip", "trap ip", "syslog ip", "trap and syslog", "snmp trap"]):
                logger.debug("Querying external IP configuration for trap and syslog")
                external_ip_config = self.get_external_ip_config()
                response_data["external_ip_config"] = external_ip_config
            
            # Check if the question is about MSD Fabric associations
            if any(term in question_lower for term in ["msd", "multi-site", "multisite", "fabric association", "fabric associations"]):
                logger.debug("Querying MSD Fabric associations")
                msd_associations = self.get_msd_fabric_associations()
                response_data["msd_fabric_associations"] = msd_associations
            
            # Check if the question is about devices/switches in NDFC
            if any(term in question_lower for term in ["device", "devices", "switch", "switches", "ndfc inventory", "all switches"]):
                logger.debug("Querying all switches/devices in NDFC")
                all_switches = self.get_all_switches()
                response_data["switches"] = all_switches
            
            # Check if the question is about comparing switch configurations
            if any(term in question_lower for term in ["compare", "comparison", "difference", "differences"]) and any(term in question_lower for term in ["config", "configuration", "settings"]) and "switch" in question_lower:
                logger.debug("Detected request to compare switch configurations")
                
                # Try to extract switch names or IDs from the question
                import re
                
                # Look for patterns like "compare switch X and Y" or "compare X with Y"
                switch_names = re.findall(r'switch\s+([a-zA-Z0-9_\-\.]+)', question_lower)
                if len(switch_names) < 2:
                    # Try alternative patterns
                    switch_names = re.findall(r'compare\s+([a-zA-Z0-9_\-\.]+)\s+(?:and|with|to)\s+([a-zA-Z0-9_\-\.]+)', question_lower)
                    if switch_names and isinstance(switch_names[0], tuple) and len(switch_names[0]) >= 2:
                        switch_names = list(switch_names[0])
                
                if len(switch_names) >= 2:
                    logger.debug(f"Extracted switch names for comparison: {switch_names[0]} and {switch_names[1]}")
                    comparison_result = self.compare_switch_configs(switch_names[0], switch_names[1])
                    response_data["switch_config_comparison"] = comparison_result
                else:
                    logger.debug("Could not extract switch names from the question")
                    response_data["switch_config_comparison"] = {
                        "error": "Could not identify which switches to compare. Please specify the switch names or IDs clearly.",
                        "example": "Example: 'Compare switch configurations between Switch1 and Switch2'"
                    }
            
            # Check if the question is about a specific switch configuration
            elif any(term in question_lower for term in ["config", "configuration", "settings"]) and "switch" in question_lower:
                logger.debug("Detected request for switch configuration")
                
                # Try to extract switch name or ID from the question
                import re
                
                # Look for patterns with "of" or "for" followed by a switch name
                # This should catch patterns like "configuration of N9K-C9300v"
                of_patterns = [
                    r'(?:config|configuration|settings)\s+of\s+([a-zA-Z0-9\-\.]+)',  # "configuration of N9K-C9300v"
                    r'(?:config|configuration|settings)\s+for\s+([a-zA-Z0-9\-\.]+)',  # "configuration for N9K-C9300v"
                    r'([a-zA-Z0-9\-\.]+)\s+(?:config|configuration|settings)',       # "N9K-C9300v configuration"
                    r'switch\s+([a-zA-Z0-9\-\.]+)'                                  # "switch N9K-C9300v"
                ]
                
                # First try the "of/for" patterns which are more specific
                switch_name = None
                for pattern in of_patterns:
                    matches = re.findall(pattern, question_lower)
                    if matches:
                        # Skip if the match is "switch" or "configuration" itself
                        if matches[0] not in ["switch", "configuration", "config", "settings"]:
                            switch_name = matches[0]
                            logger.debug(f"Extracted switch name from of/for pattern: {switch_name}")
                            break
                
                # If we didn't find a match with the of/for patterns, try to find a model name pattern
                if not switch_name:
                    # Look for model name patterns like N9K-C9300v
                    model_patterns = [
                        r'([a-zA-Z0-9]+\-[a-zA-Z0-9]+)',  # "N9K-C9300v"
                        r'([a-zA-Z0-9]+\-[a-zA-Z0-9]+\-[a-zA-Z0-9]+)'  # "N9K-C9300v-something"
                    ]
                    
                    for pattern in model_patterns:
                        matches = re.findall(pattern, question_lower)
                        if matches:
                            switch_name = matches[0]
                            logger.debug(f"Extracted switch name from model pattern: {switch_name}")
                            break
                
                # If we found a model name, check if there's a serial number in parentheses
                if switch_name:
                    # Look for a pattern like "N9K-C9300v (9H24YY16D5F)"
                    serial_in_parens = re.findall(fr'{re.escape(switch_name)}\s*\(([a-zA-Z0-9\-]+)\)', question)
                    if serial_in_parens:
                        serial_number = serial_in_parens[0]
                        logger.debug(f"Found serial number {serial_number} for switch {switch_name}")
                        # Use the serial number instead of the model name for more precise lookup
                        switch_name = serial_number
                
                if switch_name:
                    logger.debug(f"Getting configuration for switch: {switch_name}")
                    switch_config = self.get_switch_config(switch_name)
                    response_data["switch_config"] = switch_config
                else:
                    logger.debug("Could not extract switch name from the question")
                    response_data["switch_config"] = {
                        "error": "Could not identify which switch to get configuration for. Please specify the switch name or ID clearly.",
                        "example": "Example: 'Get configuration for Switch1'"
                    }
            
            # Check if the question is about a specific device by serial number or model
            elif any(term in question_lower for term in ["ip", "address", "addresses", "information", "details"]) and any(pattern in question_lower for pattern in ["serial", "model", "device", "switch"]):
                logger.debug("Detected request for device information by serial number or model")
                
                # Try to extract serial number and model from the question
                import re
                
                # First, try to extract model and serial number together using a pattern like "N9K-C9300v (9H24YY16D5F)"
                model_serial_pattern = r'([a-zA-Z0-9\-]+)\s*\(([a-zA-Z0-9\-]+)\)'
                model_serial_matches = re.findall(model_serial_pattern, question)
                
                if model_serial_matches:
                    model_name = model_serial_matches[0][0]
                    serial_number = model_serial_matches[0][1]
                    logger.debug(f"Extracted model: {model_name} and serial: {serial_number} from combined pattern")
                    
                    # First try to get device info using the serial number
                    logger.debug(f"Looking up device with serial number: {serial_number}")
                    device_info = self.get_device_by_serial(serial_number)
                    
                    # If that fails, try using the model name
                    if device_info.get("device_found", False) is False:
                        logger.debug(f"Serial number lookup failed, trying model name: {model_name}")
                        device_info = self.get_device_by_serial(model_name)
                    
                    response_data["device_info"] = device_info
                else:
                    # If we didn't find a combined pattern, look for individual patterns
                    # Look for patterns like "serial number X" or text in parentheses which might be a serial
                    serial_patterns = [
                        r'serial\s+(?:number\s+)?([a-zA-Z0-9\-]+)',  # "serial number ABC123"
                        r'serial\s*:\s*([a-zA-Z0-9\-]+)',            # "serial: ABC123"
                        r'serial\s*=\s*([a-zA-Z0-9\-]+)',            # "serial=ABC123"
                        r'\(([a-zA-Z0-9\-]+)\)',                     # "(ABC123)"
                        r'device\s+([a-zA-Z0-9\-]+)',                # "device N9K-C9300v"
                        r'switch\s+([a-zA-Z0-9\-]+)',                # "switch N9K-C9300v"
                        r'of\s+([a-zA-Z0-9\-]+)',                    # "of N9K-C9300v"
                        r'for\s+([a-zA-Z0-9\-]+)'                    # "for N9K-C9300v"
                    ]
                    
                    serial_number = None
                    model_name = None
                    
                    # First try to extract the serial number or model
                    for pattern in serial_patterns:
                        matches = re.findall(pattern, question_lower)
                        if matches:
                            identifier = matches[0]
                            if "-" in identifier:  # Likely a model name like N9K-C9300v
                                model_name = identifier
                                logger.debug(f"Extracted model name: {model_name}")
                            else:  # Likely a serial number
                                serial_number = identifier
                                logger.debug(f"Extracted serial number: {serial_number}")
                            break
                    
                    # Use the serial number if found, otherwise use the model name
                    search_term = serial_number if serial_number else model_name
                    
                    if search_term:
                        logger.debug(f"Searching for device with identifier: {search_term}")
                        device_info = self.get_device_by_serial(search_term)
                        response_data["device_info"] = device_info
                    else:
                        logger.debug("Could not extract serial number or model from the question")
                        response_data["device_info"] = {
                            "error": "Could not identify which device to get information for. Please specify the serial number or model clearly.",
                            "example": "Example: 'What is the IP address of device with serial number ABC123?'"
                        }
                
                # If we have device info but it's empty, try to get all switches and find the matching one
                if "device_info" in response_data and (not response_data["device_info"] or response_data["device_info"] == {}):
                    logger.debug("Device info is empty, trying to find device in all switches")
                    
                    # Get all switches
                    all_switches = self.get_all_switches()
                    
                    if isinstance(all_switches, dict) and "switches" in all_switches:
                        # Look for the device in the switches list
                        for switch in all_switches["switches"]:
                            # Check if this switch matches our search criteria
                            if (serial_number and switch.get("serialNumber", "").lower() == serial_number.lower()) or \
                               (model_name and switch.get("model", "").lower() == model_name.lower()) or \
                               (model_name and model_name.lower() in switch.get("model", "").lower()):
                                logger.debug(f"Found matching device in all switches list")
                                response_data["device_info"] = {
                                    "device_found": True,
                                    "device_info": switch
                                }
                                break
                    
                    # If we still don't have device info, include all switches in the response
                    if not response_data["device_info"] or response_data["device_info"] == {}:
                        logger.debug("Could not find specific device, including all switches in response")
                        response_data["switches"] = all_switches
            
            # Format the response as a JSON string
            return json.dumps(response_data, indent=2)
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error processing query: {str(e)}"
    
    def get_external_ip_config(self):
        """Get external IP configuration for trap and syslog from Nexus Dashboard."""
        try:
            # First try to get the network configuration which should include external IPs
            network_config_endpoint = "/appcenter/cisco/ndfc/api/v1/event/api/getTrapSyslogIP"
            result = self._make_request("GET", network_config_endpoint)

            # If we got a successful response, extract the trap and syslog IP information
            if not (isinstance(result, dict) and result.get("error")):
                # Extract trap and syslog IP information
                # Note: The exact structure depends on the Nexus Dashboard API response format
                # This is a generic implementation that should be adapted based on actual response
                external_ip_info = {
                    "trap_ip": self._extract_trap_ip(result),
                    "syslog_ip": self._extract_syslog_ip(result),
                    "management_ip": self._extract_management_ip(result),
                    "raw_network_config": result  # Include the raw config for debugging
                }
                return external_ip_info
            else:
                # If we couldn't get the network config, try to get the system info which might include IP information
                system_info = self.get_system_info()
                if not (isinstance(system_info, dict) and system_info.get("error")):
                    return {
                        "note": "Could not find specific trap/syslog IP configuration. Using system information instead.",
                        "system_info": system_info
                    }
                else:
                    return {"error": "Failed to retrieve external IP configuration", "details": result.get("error", "Unknown error")}
        except Exception as e:
            logger.error(f"Error getting external IP configuration: {str(e)}")
            return {"error": f"Exception while retrieving external IP configuration: {str(e)}"}
    
    def _extract_trap_ip(self, network_config):
        """Extract trap IP from network configuration."""
        # This method should be customized based on the actual response structure
        try:
            # Example implementation - adjust based on actual API response format
            if isinstance(network_config, dict):
                # Try different possible paths where trap IP might be stored
                if "trapServer" in network_config:
                    return network_config["trapServer"]
                elif "snmp" in network_config and "trapServer" in network_config["snmp"]:
                    return network_config["snmp"]["trapServer"]
                elif "networkSettings" in network_config and "snmp" in network_config["networkSettings"]:
                    return network_config["networkSettings"]["snmp"].get("trapServer", "Not configured")
            
            # If we couldn't find it in the expected locations, look for any field that might contain trap information
            if isinstance(network_config, dict):
                for key, value in network_config.items():
                    if "trap" in key.lower() and isinstance(value, str):
                        return value
            
            return "Not found in configuration"
        except Exception as e:
            logger.error(f"Error extracting trap IP: {str(e)}")
            return "Error extracting from configuration"
    
    def _extract_syslog_ip(self, network_config):
        """Extract syslog IP from network configuration."""
        # This method should be customized based on the actual response structure
        try:
            # Example implementation - adjust based on actual API response format
            if isinstance(network_config, dict):
                # Try different possible paths where syslog IP might be stored
                if "syslogServer" in network_config:
                    return network_config["syslogServer"]
                elif "syslog" in network_config and "server" in network_config["syslog"]:
                    return network_config["syslog"]["server"]
                elif "networkSettings" in network_config and "syslog" in network_config["networkSettings"]:
                    return network_config["networkSettings"]["syslog"].get("server", "Not configured")
            
            # If we couldn't find it in the expected locations, look for any field that might contain syslog information
            if isinstance(network_config, dict):
                for key, value in network_config.items():
                    if "syslog" in key.lower() and isinstance(value, str):
                        return value
            
            return "Not found in configuration"
        except Exception as e:
            logger.error(f"Error extracting syslog IP: {str(e)}")
            return "Error extracting from configuration"
    
    def _extract_management_ip(self, network_config):
        """Extract management IP from network configuration."""
        # This method should be customized based on the actual response structure
        try:
            # Example implementation - adjust based on actual API response format
            if isinstance(network_config, dict):
                # Try different possible paths where management IP might be stored
                if "managementIp" in network_config:
                    return network_config["managementIp"]
                elif "management" in network_config and "ip" in network_config["management"]:
                    return network_config["management"]["ip"]
                elif "networkSettings" in network_config and "management" in network_config["networkSettings"]:
                    return network_config["networkSettings"]["management"].get("ip", "Not configured")
            
            # If we couldn't find it in the expected locations, look for any field that might contain IP information
            if isinstance(network_config, dict):
                for key, value in network_config.items():
                    if "ip" in key.lower() and "management" in key.lower() and isinstance(value, str):
                        return value
            
            return "Not found in configuration"
        except Exception as e:
            logger.error(f"Error extracting management IP: {str(e)}")
            return "Error extracting from configuration"

    def get_msd_fabric_associations(self):
        """Get MSD Fabric associations from Nexus Dashboard."""
        try:
            # Use the endpoint provided by the user
            endpoint = "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msd/fabric-associations"
            result = self._make_request("GET", endpoint)
            
            # If we got a successful response, return it
            if not (isinstance(result, dict) and result.get("error")):
                logger.debug(f"Successfully retrieved MSD fabric associations")
                return result
            else:
                logger.error(f"Failed to retrieve MSD fabric associations: {result.get('error', 'Unknown error')}")
                return {"error": "Failed to retrieve MSD fabric associations", "details": result.get("error", "Unknown error")}
        except Exception as e:
            logger.error(f"Error getting MSD fabric associations: {str(e)}")
            return {"error": f"Exception while retrieving MSD fabric associations: {str(e)}"}

    def get_all_switches(self):
        """Get all switches/devices from Nexus Dashboard Fabric Controller (NDFC)."""
        try:
            # Use the endpoint provided by the user
            endpoint = "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/inventory/allswitches"
            result = self._make_request("GET", endpoint)
            
            # If we got a successful response, return it
            if not (isinstance(result, dict) and result.get("error")):
                logger.debug(f"Successfully retrieved all switches from NDFC")
                
                # If the response is a list, process it to extract essential information
                if isinstance(result, list):
                    logger.debug(f"Processing list of {len(result)} switches")
                    simplified_switches = []
                    for switch in result:
                        if isinstance(switch, dict):
                            # Extract the most important switch information
                            simplified_switch = {
                                "deviceName": switch.get("deviceName", "Unknown"),
                                "ipAddress": switch.get("ipAddress", "Unknown"),
                                "serialNumber": switch.get("serialNumber", "Unknown"),
                                "model": switch.get("model", "Unknown"),
                                "status": switch.get("status", "Unknown"),
                                "fabricName": switch.get("fabricName", "Unknown")
                            }
                            simplified_switches.append(simplified_switch)
                        else:
                            simplified_switches.append(str(switch))
                    
                    return {
                        "count": len(result),
                        "switches": simplified_switches
                    }
                
                return result
            else:
                logger.error(f"Failed to retrieve switches from NDFC: {result.get('error', 'Unknown error')}")
                return {"error": "Failed to retrieve switches from NDFC", "details": result.get("error", "Unknown error")}
        except Exception as e:
            logger.error(f"Error getting switches from NDFC: {str(e)}")
            return {"error": f"Exception while retrieving switches from NDFC: {str(e)}"}

    def get_switch_config(self, switch_id_or_name):
        """Get configuration for a specific switch from Nexus Dashboard.
        
        Args:
            switch_id_or_name: The switch ID, name, or IP address to get configuration for
            
        Returns:
            Dictionary containing the switch configuration details
        """
        try:
            # First, try to find the switch in the inventory to get its ID if a name was provided
            switch_id = switch_id_or_name
            if not switch_id_or_name.isdigit():  # If it's not a numeric ID, try to find by name or IP
                logger.debug(f"Looking up switch ID for: {switch_id_or_name}")
                all_switches = self.get_all_switches()
                
                if isinstance(all_switches, dict) and "switches" in all_switches:
                    for switch in all_switches["switches"]:
                        if (switch.get("serialNumber", "").lower() == switch_id_or_name.lower() or 
                            switch.get("deviceName", "").lower() == switch_id_or_name.lower() or 
                            switch.get("ipAddress", "") == switch_id_or_name):
                            # Found the switch, use its ID for the config request
                            if "serialNumber" in switch:
                                switch_id = switch["serialNumber"]
                                logger.debug(f"Found switch ID: {switch_id} for {switch_id_or_name}")
                                break
                
            # Endpoint to get switch configuration
            endpoint = f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/inventory/getconfigs/{switch_id}"
            logger.debug(f"Getting configuration for switch ID: {switch_id}")
            result = self._make_request("GET", endpoint)
            
            # If we got a successful response, return it
            if not (isinstance(result, dict) and result.get("error")):
                logger.debug(f"Successfully retrieved configuration for switch: {switch_id}")
                
                # Process the configuration data
                if isinstance(result, dict):
                    # Return a structured view of the configuration
                    return {
                        "switch_id": switch_id,
                        "switch_name": switch_id_or_name,
                        "configuration": result
                    }
                else:
                    return {
                        "switch_id": switch_id,
                        "switch_name": switch_id_or_name,
                        "configuration": str(result)
                    }
            else:
                logger.error(f"Failed to retrieve configuration for switch {switch_id}: {result.get('error', 'Unknown error')}")
                
                # Try an alternative endpoint if the first one failed
                alternative_endpoint = f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/switches/{switch_id}/config"
                logger.debug(f"Trying alternative endpoint for switch config: {alternative_endpoint}")
                alt_result = self._make_request("GET", alternative_endpoint)
                
                if not (isinstance(alt_result, dict) and alt_result.get("error")):
                    logger.debug(f"Successfully retrieved configuration from alternative endpoint")
                    return {
                        "switch_id": switch_id,
                        "switch_name": switch_id_or_name,
                        "configuration": alt_result
                    }
                
                # If both config endpoints failed, try to get basic info from inventory
                logger.debug(f"Configuration endpoints failed, falling back to basic device information")
                
                # Look for the switch in the inventory we already retrieved
                if isinstance(all_switches, dict) and "switches" in all_switches:
                    for switch in all_switches["switches"]:
                        if (switch.get("serialNumber", "").lower() == switch_id.lower() or
                            switch.get("deviceName", "").lower() == switch_id_or_name.lower() or
                            switch.get("ipAddress", "") == switch_id_or_name):
                            
                            logger.debug(f"Found basic device information in inventory")
                            return {
                                "switch_id": switch_id,
                                "switch_name": switch_id_or_name,
                                "note": "Could not retrieve detailed configuration. The switch may be unreachable or the configuration API may not be available.",
                                "basic_info": switch,
                                "status": "Limited information available"
                            }
                
                # Try one more endpoint for running config
                running_config_endpoint = f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/switches/{switch_id}/running-config"
                logger.debug(f"Trying running config endpoint: {running_config_endpoint}")
                running_result = self._make_request("GET", running_config_endpoint)
                
                if not (isinstance(running_result, dict) and running_result.get("error")):
                    logger.debug(f"Successfully retrieved running configuration")
                    return {
                        "switch_id": switch_id,
                        "switch_name": switch_id_or_name,
                        "configuration": running_result,
                        "config_type": "running-config"
                    }
                
                return {"error": f"Failed to retrieve configuration for switch {switch_id_or_name}", "details": result.get("error", "Unknown error")}
            
        except Exception as e:
            logger.error(f"Error getting switch configuration: {str(e)}")
            return {"error": f"Exception while retrieving switch configuration: {str(e)}"}

    def compare_switch_configs(self, switch1_id_or_name, switch2_id_or_name):
        """Compare configurations between two switches.
        
        Args:
            switch1_id_or_name: The ID, name, or IP of the first switch
            switch2_id_or_name: The ID, name, or IP of the second switch
            
        Returns:
            Dictionary containing the comparison results
        """
        try:
            logger.debug(f"Comparing configurations between {switch1_id_or_name} and {switch2_id_or_name}")
            
            # Get configurations for both switches
            switch1_config = self.get_switch_config(switch1_id_or_name)
            switch2_config = self.get_switch_config(switch2_id_or_name)
            
            # Check if we got valid configurations
            if "error" in switch1_config:
                return {"error": f"Failed to get configuration for first switch: {switch1_config.get('error', 'Unknown error')}"}
            
            if "error" in switch2_config:
                return {"error": f"Failed to get configuration for second switch: {switch2_config.get('error', 'Unknown error')}"}
            
            # Compare the configurations
            comparison_result = {
                "switch1": {
                    "id": switch1_config.get("switch_id"),
                    "name": switch1_config.get("switch_name")
                },
                "switch2": {
                    "id": switch2_config.get("switch_id"),
                    "name": switch2_config.get("switch_name")
                },
                "differences": {},
                "similarities": {}
            }
            
            # Get the configuration sections from both switches
            config1 = switch1_config.get("configuration", {})
            config2 = switch2_config.get("configuration", {})
            
            # Compare configuration sections
            all_keys = set(config1.keys()).union(set(config2.keys()))
            
            for key in all_keys:
                # If the key exists in both configs
                if key in config1 and key in config2:
                    # If the values are the same
                    if config1[key] == config2[key]:
                        comparison_result["similarities"][key] = config1[key]
                    else:
                        comparison_result["differences"][key] = {
                            "switch1": config1[key],
                            "switch2": config2[key]
                        }
                # If the key only exists in config1
                elif key in config1:
                    comparison_result["differences"][key] = {
                        "switch1": config1[key],
                        "switch2": "Not configured"
                    }
                # If the key only exists in config2
                else:
                    comparison_result["differences"][key] = {
                        "switch1": "Not configured",
                        "switch2": config2[key]
                    }
            
            return comparison_result
            
        except Exception as e:
            logger.error(f"Error comparing switch configurations: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"error": f"Exception while comparing switch configurations: {str(e)}"}

    def get_device_by_serial(self, serial_number_or_model):
        """Get device information by serial number or model from Nexus Dashboard.
        
        Args:
            serial_number_or_model: The serial number or model of the device to look up
            
        Returns:
            Dictionary containing the device information or error details
        """
        try:
            logger.debug(f"Looking up device with identifier: {serial_number_or_model}")
            
            # First try to find the device in the inventory
            all_switches = self.get_all_switches()
            
            if isinstance(all_switches, dict) and "switches" in all_switches:
                # Look for the device in the switches list
                for switch in all_switches["switches"]:
                    # Check for match by serial number
                    if switch.get("serialNumber", "").lower() == serial_number_or_model.lower():
                        logger.debug(f"Found device with serial number {serial_number_or_model} in inventory")
                        return {
                            "device_found": True,
                            "device_info": switch
                        }
                    # Check for match by model
                    elif switch.get("model", "").lower() == serial_number_or_model.lower():
                        logger.debug(f"Found device with model {serial_number_or_model} in inventory")
                        return {
                            "device_found": True,
                            "device_info": switch
                        }
                    # Check for partial match by model
                    elif serial_number_or_model.lower() in switch.get("model", "").lower():
                        logger.debug(f"Found device with partial model match {serial_number_or_model} in inventory")
                        return {
                            "device_found": True,
                            "device_info": switch
                        }
                    # Check for match by device name
                    elif switch.get("deviceName", "").lower() == serial_number_or_model.lower():
                        logger.debug(f"Found device with name {serial_number_or_model} in inventory")
                        return {
                            "device_found": True,
                            "device_info": switch
                        }
            
            # If not found in the basic inventory, try a more specific endpoint
            endpoint = f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/inventory/devices"
            logger.debug(f"Querying devices endpoint for identifier: {serial_number_or_model}")
            result = self._make_request("GET", endpoint)
            
            # If we got a successful response, search for the device by serial number or model
            if not (isinstance(result, dict) and result.get("error")):
                if isinstance(result, list):
                    for device in result:
                        if isinstance(device, dict):
                            # Check for match by serial number
                            if device.get("serialNumber", "").lower() == serial_number_or_model.lower():
                                logger.debug(f"Found device with serial number {serial_number_or_model} in devices endpoint")
                                return {
                                    "device_found": True,
                                    "device_info": device
                                }
                            # Check for match by model
                            elif device.get("model", "").lower() == serial_number_or_model.lower():
                                logger.debug(f"Found device with model {serial_number_or_model} in devices endpoint")
                                return {
                                    "device_found": True,
                                    "device_info": device
                                }
                            # Check for partial match by model
                            elif serial_number_or_model.lower() in device.get("model", "").lower():
                                logger.debug(f"Found device with partial model match {serial_number_or_model} in devices endpoint")
                                return {
                                    "device_found": True,
                                    "device_info": device
                                }
                
                # Try another endpoint format if the first one didn't find the device
                alt_endpoint = f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/devices/{serial_number_or_model}"
                logger.debug(f"Trying alternative endpoint for device: {alt_endpoint}")
                alt_result = self._make_request("GET", alt_endpoint)
                
                if not (isinstance(alt_result, dict) and alt_result.get("error")):
                    logger.debug(f"Found device with identifier {serial_number_or_model} in alternative endpoint")
                    return {
                        "device_found": True,
                        "device_info": alt_result
                    }
            
            # If we still haven't found the device, try one more endpoint format
            final_endpoint = f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/inventory/manageddevices?serialNumber={serial_number_or_model}"
            logger.debug(f"Trying final endpoint for device: {final_endpoint}")
            final_result = self._make_request("GET", final_endpoint)
            
            if not (isinstance(final_result, dict) and final_result.get("error")):
                if isinstance(final_result, list) and len(final_result) > 0:
                    logger.debug(f"Found device with identifier {serial_number_or_model} in final endpoint")
                    return {
                        "device_found": True,
                        "device_info": final_result[0] if isinstance(final_result[0], dict) else final_result
                    }
            
            # Try a direct query for the model name
            model_endpoint = f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/inventory/switches?model={serial_number_or_model}"
            logger.debug(f"Trying model-specific endpoint: {model_endpoint}")
            model_result = self._make_request("GET", model_endpoint)
            
            if not (isinstance(model_result, dict) and model_result.get("error")):
                if isinstance(model_result, list) and len(model_result) > 0:
                    logger.debug(f"Found device with model {serial_number_or_model} in model-specific endpoint")
                    return {
                        "device_found": True,
                        "device_info": model_result[0] if isinstance(model_result[0], dict) else model_result
                    }
            
            # If we've tried all endpoints and still haven't found the device
            logger.error(f"Device with identifier {serial_number_or_model} not found in any endpoint")
            return {
                "device_found": False,
                "error": f"Device with identifier {serial_number_or_model} not found in Nexus Dashboard inventory",
                "note": "The Nexus Dashboard API might not have information about this device. Please verify the serial number or model name and try again."
            }
            
        except Exception as e:
            logger.error(f"Error getting device by identifier: {str(e)}")
            return {"error": f"Exception while retrieving device information: {str(e)}"}
