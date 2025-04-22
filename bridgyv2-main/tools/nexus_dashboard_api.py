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
                
            # Format the response as a JSON string
            return json.dumps(response_data, indent=2)
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error processing query: {str(e)}"
