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
            
            # Initialize session and token
            self.session = requests.Session()
            self.session.verify = False  # Skip SSL verification
            self.token = None
            self.token_expiry = 0
            
            # Authenticate immediately
            self._authenticate()
            self.initialization_failed = False
            self.error_message = None
            
        except Exception as e:
            logger.error(f"Error initializing Nexus Dashboard API: {str(e)}")
            self.initialization_failed = True
            self.error_message = str(e)
    
    def _authenticate(self):
        """Authenticate with Nexus Dashboard and get token."""
        try:
            current_time = time.time()
            
            # If token exists and is not expired, skip authentication
            if self.token and current_time < self.token_expiry:
                logger.debug("Using existing token")
                return
                
            logger.debug(f"Authenticating to Nexus Dashboard at {self.base_url}")
            
            # Ensure base_url doesn't end with a trailing slash
            auth_url = f"{self.base_url}/api/v1/auth/login"
            
            payload = {
                "username": self.username,
                "password": self.password
            }
            
            logger.debug(f"Making authentication request to {auth_url}")
            
            # Set a reasonable timeout for the request
            response = self.session.post(auth_url, json=payload, timeout=30)
            
            # Log response status
            logger.debug(f"Authentication response status: {response.status_code}")
            
            # Check for HTTP errors
            if response.status_code != 200:
                logger.error(f"Authentication failed with status code {response.status_code}")
                logger.error(f"Response content: {response.text[:200]}")  # Log first 200 chars of response
                raise Exception(f"Authentication failed with status code {response.status_code}")
                
            try:
                auth_data = response.json()
                logger.debug("Successfully parsed authentication response")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse authentication response: {str(e)}")
                logger.error(f"Response content: {response.text[:200]}")
                raise Exception(f"Failed to parse authentication response: {str(e)}")
            
            self.token = auth_data.get("token")
            
            if not self.token:
                logger.error("Authentication response did not contain a token")
                logger.error(f"Response content: {auth_data}")
                raise Exception("Authentication failed: No token received")
                
            # Set token expiry (default to 30 minutes if not specified)
            expiry_seconds = auth_data.get("expiry", 1800)
            self.token_expiry = current_time + expiry_seconds
            
            # Set authorization header for future requests
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            logger.debug("Authentication successful, token received and stored")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during authentication: {str(e)}")
            raise Exception(f"Network error during authentication: {str(e)}")
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise
    
    def _make_request(self, method, endpoint, params=None, data=None):
        """Make an API request with authentication."""
        try:
            # Ensure we have a valid token
            self._authenticate()
            
            # Ensure endpoint starts with a slash
            if not endpoint.startswith('/'):
                endpoint = '/' + endpoint
                
            url = f"{self.base_url}{endpoint}"
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
                # Token might be expired, force re-authentication
                logger.info("Received 401 Unauthorized, attempting to refresh token")
                self.token = None
                self.token_expiry = 0
                # Try once more
                self._authenticate()
                logger.info("Re-authenticated, retrying request")
                return self._make_request(method, endpoint, params, data)
            return {"error": str(e), "status_code": e.response.status_code}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during request: {str(e)}")
            return {"error": f"Network error: {str(e)}"}
            
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return {"error": str(e)}
    
    def get_sites(self):
        """Get list of sites from Nexus Dashboard."""
        return self._make_request("GET", "/api/v1/sites")
    
    def get_fabrics(self):
        """Get list of fabrics from Nexus Dashboard."""
        return self._make_request("GET", "/api/v1/fabrics")
    
    def get_devices(self):
        """Get list of devices from Nexus Dashboard."""
        return self._make_request("GET", "/api/v1/devices")
    
    def get_telemetry(self, metric_type, time_range="1h"):
        """Get telemetry data from Nexus Dashboard."""
        params = {
            "type": metric_type,
            "timeRange": time_range
        }
        return self._make_request("GET", "/api/v1/telemetry", params=params)
    
    def get_alarms(self, severity=None, time_range="24h"):
        """Get alarms from Nexus Dashboard."""
        params = {
            "timeRange": time_range
        }
        if severity:
            params["severity"] = severity
        return self._make_request("GET", "/api/v1/alarms", params=params)
    
    def get_workflows(self, status=None):
        """Get automation workflows from Nexus Dashboard."""
        params = {}
        if status:
            params["status"] = status
        return self._make_request("GET", "/api/v1/workflows", params=params)
    
    def execute_workflow(self, workflow_id, parameters=None):
        """Execute an automation workflow in Nexus Dashboard."""
        data = {
            "workflowId": workflow_id
        }
        if parameters:
            data["parameters"] = parameters
        return self._make_request("POST", "/api/v1/workflows/execute", data=data)
    
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
