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
            self.api_key = os.getenv("NEXUS_DASHBOARD_API_KEY")
            
            logger.debug(f"Environment variables loaded: URL={bool(self.base_url)}, API Key={bool(self.api_key)}")
            
            if not self.base_url or not self.api_key:
                missing_vars = []
                if not self.base_url:
                    missing_vars.append("NEXUS_DASHBOARD_URL")
                if not self.api_key:
                    missing_vars.append("NEXUS_DASHBOARD_API_KEY")
                    
                error_msg = f"Nexus Dashboard credentials not found in environment variables: {', '.join(missing_vars)}"
                logger.error(error_msg)
                self.initialization_failed = True
                self.error_message = error_msg
                return
                
            logger.debug(f"Nexus Dashboard URL: {self.base_url}")
            logger.debug(f"Nexus Dashboard API Key: {'*' * 8}{self.api_key[-4:] if self.api_key else ''}")
            
            # Initialize session
            self.session = requests.Session()
            self.session.verify = False  # Skip SSL verification
            
            # Set API key in the headers
            self.session.headers.update({
                "X-Auth-Token": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json"
            })
            
            # Discover available API endpoints
            self.discover_api_endpoints()
            
            self.initialization_failed = False
            self.error_message = None
            
        except Exception as e:
            logger.error(f"Error initializing Nexus Dashboard API: {str(e)}")
            self.initialization_failed = True
            self.error_message = str(e)
    
    def discover_api_endpoints(self):
        """Discover available API endpoints by checking the API documentation."""
        try:
            logger.debug("Discovering available API endpoints")
            
            # Try to access the API documentation
            apidocs_url = f"{self.base_url}/apidocs/"
            logger.debug(f"Checking API documentation at {apidocs_url}")
            
            # Store discovered endpoints
            self.endpoints = {
                # Default platform endpoints
                "platform": {
                    "base": "",
                    "sites": "/api/v1/sites",
                    "devices": "/api/v1/devices",
                    "fabrics": "/api/v1/fabrics",
                    "telemetry": "/api/v1/telemetry",
                    "alarms": "/api/v1/alarms",
                    "workflows": "/api/v1/workflows",
                    "execute_workflow": "/api/v1/workflows/execute"
                },
                # Nexus Dashboard Orchestrator endpoints
                "ndo": {
                    "base": "/mso",
                    "sites": "/api/v1/sites",
                    "schemas": "/api/v1/schemas",
                    "tenants": "/api/v1/tenants"
                },
                # Nexus Dashboard Insights endpoints
                "ndi": {
                    "base": "/sedgeapi/v1/cisco-nir/api",
                    "telemetry": "/api/telemetry/v2/config",
                    "alerts": "/api/telemetry/v2/alerts"
                },
                # Nexus Dashboard Fabric Controller endpoints
                "ndfc": {
                    "base": "/appcenter/cisco/ndfc",
                    "fabrics": "/api/v1/lan-fabric/rest/control/fabrics"
                }
            }
            
            logger.debug(f"API endpoints initialized with default values")
            
        except Exception as e:
            logger.error(f"Error discovering API endpoints: {str(e)}")
            # Continue with default endpoints
    
    def _validate_api_key(self):
        """Validate the API key by making a test request."""
        try:
            logger.debug("Validating API key with a test request")
            
            # Try to access a simple endpoint that requires authentication
            # First try platform health endpoint
            test_endpoint = "/api/v1/platform/health"
            url = f"{self.base_url}{test_endpoint}"
            
            logger.debug(f"Making validation request to {url}")
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 401 or response.status_code == 403:
                logger.error(f"API key validation failed with status code {response.status_code}")
                raise Exception(f"Invalid API key. Authentication failed with status code {response.status_code}")
                
            logger.debug(f"API key validation successful with status code {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during API key validation: {str(e)}")
            raise Exception(f"Network error during API key validation: {str(e)}")
        except Exception as e:
            logger.error(f"API key validation error: {str(e)}")
            raise

    def _make_request(self, method, endpoint, service="platform", params=None, data=None):
        """Make an API request with authentication.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            service: Service name (platform, ndo, ndi, ndfc)
            params: Query parameters
            data: Request body data
        """
        try:
            # Get the base path for the service
            service_base = self.endpoints.get(service, {}).get("base", "")
            
            # Ensure endpoint starts with a slash
            if not endpoint.startswith('/'):
                endpoint = '/' + endpoint
                
            # Construct the full URL
            url = f"{self.base_url}{service_base}{endpoint}"
            logger.debug(f"Making {method} request to {url}")
            
            if params:
                logger.debug(f"Request params: {params}")
            if data:
                logger.debug(f"Request data: {json.dumps(data)[:200]}")  # Log first 200 chars
                
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30  # Set a reasonable timeout
            )
            
            logger.debug(f"Response status code: {response.status_code}")
            
            # Check for HTTP errors
            if response.status_code >= 400:
                logger.error(f"HTTP error: {response.status_code}")
                logger.error(f"Response content: {response.text[:200]}")  # Log first 200 chars
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
    
    def get_sites(self):
        """Get list of sites from Nexus Dashboard."""
        # Try platform sites endpoint
        response = self._make_request("GET", self.endpoints["platform"]["sites"], service="platform")
        
        # If that fails, try NDO sites endpoint
        if isinstance(response, dict) and response.get("error"):
            logger.debug("Platform sites endpoint failed, trying NDO sites endpoint")
            response = self._make_request("GET", self.endpoints["ndo"]["sites"], service="ndo")
            
        return response
    
    def get_fabrics(self):
        """Get list of fabrics from Nexus Dashboard."""
        # Try platform fabrics endpoint
        response = self._make_request("GET", self.endpoints["platform"]["fabrics"], service="platform")
        
        # If that fails, try NDFC fabrics endpoint
        if isinstance(response, dict) and response.get("error"):
            logger.debug("Platform fabrics endpoint failed, trying NDFC fabrics endpoint")
            response = self._make_request("GET", self.endpoints["ndfc"]["fabrics"], service="ndfc")
            
        return response
    
    def get_devices(self):
        """Get list of devices from Nexus Dashboard."""
        return self._make_request("GET", self.endpoints["platform"]["devices"], service="platform")
    
    def get_telemetry(self, metric_type, time_range="1h"):
        """Get telemetry data from Nexus Dashboard."""
        params = {
            "type": metric_type,
            "timeRange": time_range
        }
        
        # Try platform telemetry endpoint
        response = self._make_request("GET", self.endpoints["platform"]["telemetry"], service="platform", params=params)
        
        # If that fails, try NDI telemetry endpoint
        if isinstance(response, dict) and response.get("error"):
            logger.debug("Platform telemetry endpoint failed, trying NDI telemetry endpoint")
            response = self._make_request("GET", self.endpoints["ndi"]["telemetry"], service="ndi", params=params)
            
        return response
    
    def get_alarms(self, severity=None, time_range="24h"):
        """Get alarms from Nexus Dashboard."""
        params = {
            "timeRange": time_range
        }
        if severity:
            params["severity"] = severity
            
        # Try platform alarms endpoint
        response = self._make_request("GET", self.endpoints["platform"]["alarms"], service="platform", params=params)
        
        # If that fails, try NDI alerts endpoint
        if isinstance(response, dict) and response.get("error"):
            logger.debug("Platform alarms endpoint failed, trying NDI alerts endpoint")
            response = self._make_request("GET", self.endpoints["ndi"]["alerts"], service="ndi", params=params)
            
        return response
    
    def get_workflows(self, status=None):
        """Get automation workflows from Nexus Dashboard."""
        params = {}
        if status:
            params["status"] = status
            
        return self._make_request("GET", self.endpoints["platform"]["workflows"], service="platform", params=params)
    
    def execute_workflow(self, workflow_id, parameters=None):
        """Execute an automation workflow in Nexus Dashboard."""
        data = {
            "workflowId": workflow_id
        }
        if parameters:
            data["parameters"] = parameters
            
        return self._make_request("POST", self.endpoints["platform"]["execute_workflow"], service="platform", data=data)
    
    def query(self, question: str) -> str:
        """Process a natural language query about Nexus Dashboard."""
        if self.initialization_failed:
            return f"Error: Nexus Dashboard API initialization failed. {self.error_message}"
        
        try:
            # Process the question to determine what data to fetch
            question_lower = question.lower()
            
            response_data = {}
            
            # Check for different query types and fetch relevant data
            if any(term in question_lower for term in ["site", "sites", "location"]):
                response_data["sites"] = self.get_sites()
                
            if any(term in question_lower for term in ["fabric", "fabrics", "network fabric"]):
                response_data["fabrics"] = self.get_fabrics()
                
            if any(term in question_lower for term in ["device", "devices", "switch", "switches"]):
                response_data["devices"] = self.get_devices()
                
            if any(term in question_lower for term in ["telemetry", "metric", "metrics", "performance"]):
                # Determine metric type from question
                metric_type = "utilization"  # Default
                if "cpu" in question_lower:
                    metric_type = "cpu"
                elif "memory" in question_lower:
                    metric_type = "memory"
                elif "interface" in question_lower or "port" in question_lower:
                    metric_type = "interface"
                    
                response_data["telemetry"] = self.get_telemetry(metric_type)
                
            if any(term in question_lower for term in ["alarm", "alarms", "alert", "alerts", "error"]):
                # Determine severity from question
                severity = None
                if "critical" in question_lower:
                    severity = "critical"
                elif "major" in question_lower:
                    severity = "major"
                elif "minor" in question_lower:
                    severity = "minor"
                    
                response_data["alarms"] = self.get_alarms(severity)
                
            if any(term in question_lower for term in ["workflow", "workflows", "automation"]):
                response_data["workflows"] = self.get_workflows()
                
            # If no specific data was requested, get a general overview
            if not response_data:
                response_data = {
                    "sites": self.get_sites(),
                    "devices": self.get_devices(),
                    "alarms": self.get_alarms(severity="critical")
                }
                
            # Format the response as a JSON string
            return json.dumps(response_data, indent=2)
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return f"Error processing query: {str(e)}"
