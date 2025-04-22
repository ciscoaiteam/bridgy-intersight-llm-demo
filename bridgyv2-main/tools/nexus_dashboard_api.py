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
            "sites": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/sites",
            "devices": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/devices",
            
            # System Information
            "health": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/system/health",
            "system_info": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/system/info",
            
            # Telemetry
            "telemetry": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/telemetry/metrics",
            
            # Alarms
            "alarms": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/alarms",
            
            # Workflows
            "workflows": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/workflows",
            
            # Users
            "users": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/users",
            
            # Federation
            "federation": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/federation/members"
        }
        
        # Define fallback endpoints for different API versions
        self.fallback_endpoints = {
            "health_v3": "/appcenter/cisco/ndfc/api/v3/system/health",
            "health_v2": "/appcenter/cisco/ndfc/api/v2/system/health",
            "health_v1": "/api/v1/system/health"
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
    
    def get_system_health(self):
        """Get system health information from Nexus Dashboard."""
        # Try the primary endpoint first
        result = self._make_request("GET", self.endpoints["health"])
        
        # If the primary endpoint fails with a 404, try fallback endpoints
        if result.get("error") and "404" in result.get("error", ""):
            logger.debug("Primary health endpoint failed, trying fallback endpoints")
            
            # Try v3 endpoint
            result = self._make_request("GET", self.fallback_endpoints["health_v3"])
            if not result.get("error"):
                return result
                
            # Try v2 endpoint
            result = self._make_request("GET", self.fallback_endpoints["health_v2"])
            if not result.get("error"):
                return result
                
            # Try v1 endpoint
            result = self._make_request("GET", self.fallback_endpoints["health_v1"])
            
        return result
    
    def get_sites(self):
        """Get list of sites from Nexus Dashboard."""
        return self._make_request("GET", self.endpoints["sites"])
    
    def get_fabrics(self):
        """Get list of fabrics from Nexus Dashboard."""
        # Try the primary endpoint first with POST and empty body
        result = self._make_request("POST", self.endpoints["fabrics"], data={})
        
        # If the primary endpoint fails, try fallback endpoints
        if result.get("error"):
            logger.debug("Primary fabrics endpoint failed, trying fallback endpoints")
            
            # Try v3 endpoint
            result = self._make_request("POST", self.fallback_endpoints["fabrics_v3"], data={})
            if not result.get("error"):
                return result
                
            # Try v2 endpoint
            result = self._make_request("POST", self.fallback_endpoints["fabrics_v2"], data={})
            if not result.get("error"):
                return result
                
            # Try v1 endpoint with GET instead of POST
            result = self._make_request("GET", self.fallback_endpoints["fabrics_v1"])
            
        return result
    
    def get_devices(self):
        """Get list of devices from Nexus Dashboard."""
        return self._make_request("GET", self.endpoints["devices"])
    
    def get_telemetry(self, metric_type, time_range="1h"):
        """Get telemetry data from Nexus Dashboard."""
        params = {
            "type": metric_type,
            "timeRange": time_range
        }
        return self._make_request("GET", self.endpoints["telemetry"], params=params)
    
    def get_alarms(self, severity=None, time_range="24h"):
        """Get alarms from Nexus Dashboard."""
        params = {
            "timeRange": time_range
        }
        if severity:
            params["severity"] = severity
        return self._make_request("GET", self.endpoints["alarms"], params=params)
    
    def get_workflows(self, status=None):
        """Get automation workflows from Nexus Dashboard."""
        params = {}
        if status:
            params["status"] = status
        return self._make_request("GET", self.endpoints["workflows"], params=params)
    
    def execute_workflow(self, workflow_id, parameters=None):
        """Execute an automation workflow in Nexus Dashboard."""
        data = {
            "workflowId": workflow_id
        }
        if parameters:
            data["parameters"] = parameters
        return self._make_request("POST", self.endpoints["execute_workflow"], data=data)
    
    def get_system_info(self):
        """Get system information from Nexus Dashboard."""
        return self._make_request("GET", self.endpoints["system_info"])
    
    def get_users(self):
        """Get list of users from Nexus Dashboard."""
        return self._make_request("GET", self.endpoints["users"])
    
    def get_federation_members(self):
        """Get list of federation members from Nexus Dashboard."""
        return self._make_request("GET", self.endpoints["federation"])
    
    def query(self, question: str) -> str:
        """Process a natural language query about Nexus Dashboard."""
        if self.initialization_failed:
            return f"Error: Nexus Dashboard API initialization failed. {self.error_message}"
        
        try:
            # Process the question to determine what data to fetch
            question_lower = question.lower()
            
            response_data = {}
            
            # First get system health for a general overview
            response_data["system_health"] = self.get_system_health()
            
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
                
            if any(term in question_lower for term in ["user", "users", "account", "accounts"]):
                response_data["users"] = self.get_users()
                
            if any(term in question_lower for term in ["system", "info", "information", "status"]):
                response_data["system_info"] = self.get_system_info()
                
            if any(term in question_lower for term in ["federation", "member", "members", "cluster"]):
                response_data["federation_members"] = self.get_federation_members()
                
            # Format the response as a JSON string
            return json.dumps(response_data, indent=2)
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return f"Error processing query: {str(e)}"
