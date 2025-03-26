
from __future__ import annotations

import os
import json
import logging
from typing import Dict, List, Any, Optional
import time
import tempfile

import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Suppress insecure request warnings
urllib3.disable_warnings(InsecureRequestWarning)

import intersight
from intersight.api_client import ApiClient
from intersight.configuration import Configuration
import intersight.signing
from intersight.api.compute_api import ComputeApi
from intersight.api.asset_api import AssetApi
from intersight.api.network_api import NetworkApi
from intersight.api.virtualization_api import VirtualizationApi
from intersight.api.firmware_api import FirmwareApi
from intersight.rest import ApiException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntersightClientTool:
    """Tool for interacting with Cisco Intersight API."""
    
    def __init__(self):
        """Initialize the Intersight client."""
        try:
            # Get API key from environment variables
            api_key_id = os.getenv("INTERSIGHT_API_KEY")
            
            if not api_key_id:
                raise Exception("Intersight API key ID not found in environment variables")
                
            # Use the existing PEM file directly
            key_path = "intersight_secret_key.pem"
            
            if not os.path.isfile(key_path):
                raise Exception(f"PEM file not found at {key_path}")
                
            logger.info(f"Using PEM file: {key_path}")
            
            # Create a temporary file with the proper formatting that the library can read
            with open(key_path, 'r') as original_key_file:
                private_key_content = original_key_file.read().strip()
                
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                temp_key_path = temp_file.name
                temp_file.write(private_key_content)
                
            # Configure API key authentication with the temporary key file
            self.configuration = intersight.configuration.Configuration(
                host="https://intersight.com",
                signing_info=intersight.signing.HttpSigningConfiguration(
                    key_id=api_key_id,
                    private_key_path=temp_key_path,  # Use the temporary file with correct formatting
                    signing_scheme=intersight.signing.SCHEME_HS2019,
                    signing_algorithm=intersight.signing.ALGORITHM_ECDSA_MODE_FIPS_186_3,
                    hash_algorithm=intersight.signing.HASH_SHA256,
                    signed_headers=[
                        intersight.signing.HEADER_REQUEST_TARGET,
                        intersight.signing.HEADER_HOST,
                        intersight.signing.HEADER_DATE,
                        intersight.signing.HEADER_DIGEST
                    ]
                )
            )

            self.configuration.verify_ssl = True

            # Create API client with the configuration
            self.api_client = ApiClient(self.configuration)
            
            # Clean up only the temporary key file, not the original
            try:
                os.unlink(temp_key_path)
                logger.info("Cleaned up temporary key file")
            except Exception as clean_error:
                logger.warning(f"Could not remove temporary key file: {str(clean_error)}")

        except Exception as e:
            logger.error(f"Error initializing Intersight client: {str(e)}")
            # Clean up temp file in case of error
            if 'temp_key_path' in locals():
                try:
                    os.unlink(temp_key_path)
                except:
                    pass
            raise

    def get_servers(self) -> List[Dict[str, Any]]:
        """Get list of servers from Intersight."""
        try:
            api_instance = ComputeApi(self.api_client)
            response = api_instance.get_compute_physical_summary_list()
            
            servers = []
            for server in response.results:
                server_info = {
                    "name": server.name,
                    "serial": server.serial,
                    "model": server.model,
                    "power_state": getattr(server, "oper_power_state", "Unknown")
                }
                
                # Add optional attributes only if they exist
                if hasattr(server, "management_ip"):
                    server_info["management_ip"] = server.management_ip
                if hasattr(server, "firmware"):
                    server_info["firmware"] = server.firmware
                
                servers.append(server_info)
                
            return servers
        except Exception as e:
            return {"error": str(e)}
            
    def get_virtual_machines(self) -> List[Dict[str, Any]]:
        """Get list of virtual machines from Intersight."""
        try:
            api_instance = VirtualizationApi(self.api_client)
            response = api_instance.get_virtualization_virtual_machine_list()
            
            vms = []
            for vm in response.results:
                vm_info = {
                    "name": getattr(vm, "name", "N/A"),
                    "power_state": getattr(vm, "power_state", "N/A"),
                    "uuid": getattr(vm, "uuid", "N/A")
                }
                
                # Add optional attributes only if they exist
                if hasattr(vm, "memory"):
                    vm_info["memory"] = vm.memory
                if hasattr(vm, "cpu"):
                    vm_info["cpu"] = vm.cpu
                if hasattr(vm, "host_name"):
                    vm_info["host_name"] = vm.host_name
                    
                vms.append(vm_info)
                
            return vms
        except Exception as e:
            return {"error": str(e)}
            
    def get_device_connectors(self) -> List[Dict[str, Any]]:
        """Get list of device connectors from Intersight."""
        try:
            api_instance = AssetApi(self.api_client)
            response = api_instance.get_asset_device_registration_list()
            
            connectors = []
            for device in response.results:
                connector_info = {
                    "device_type": getattr(device, "device_type", "N/A"),
                    "platform_type": getattr(device, "platform_type", "N/A"),
                    "connection_status": getattr(device, "connection_status", "N/A"),
                    "connection_reason": getattr(device, "connection_reason", "N/A")
                }
                
                # Add device identification if available
                if hasattr(device, "device_hostname"):
                    connector_info["device_hostname"] = device.device_hostname
                if hasattr(device, "serial"):
                    connector_info["serial"] = device.serial
                
                connectors.append(connector_info)
                
            return connectors
        except Exception as e:
            return {"error": str(e)}
            
    def get_network_elements(self) -> List[Dict[str, Any]]:
        """Get list of network elements from Intersight."""
        try:
            api_instance = NetworkApi(self.api_client)
            response = api_instance.get_network_element_list()
            
            elements = []
            for element in response.results:
                # Build dictionary with safe attribute access
                network_element = {}
                
                # Add attributes that are available, with safe fallbacks
                if hasattr(element, "model"):
                    network_element["model"] = element.model
                else:
                    network_element["model"] = "N/A"
                    
                if hasattr(element, "serial"):
                    network_element["serial"] = element.serial
                else:
                    network_element["serial"] = "N/A"
                    
                if hasattr(element, "management_ip"):
                    network_element["management_ip"] = element.management_ip
                else:
                    network_element["management_ip"] = "N/A"
                    
                if hasattr(element, "version"):
                    network_element["version"] = element.version
                else:
                    network_element["version"] = "N/A"
                
                # Add device ID as fallback for name
                if hasattr(element, "device_id"):
                    network_element["device_id"] = element.device_id
                else:
                    network_element["device_id"] = "Unknown Device"
                
                elements.append(network_element)
                
            return elements
        except Exception as e:
            return {"error": str(e)}
            
    def get_health_alerts(self) -> List[Dict[str, Any]]:
        """Get health and alerting information from Intersight."""
        try:
            # Use both CondAPI and direct API call as fallback
            logger.info("Attempting to fetch health alerts via CondApi...")
            
            try:
                from intersight.api.cond_api import CondApi
                api_instance = CondApi(self.api_client)
                
                # Get alarms list with detailed logging
                logger.info("Calling get_cond_alarm_list API...")
                response = api_instance.get_cond_alarm_list()
                
                # Log the response structure for debugging
                logger.info(f"Response type: {type(response)}")
                if hasattr(response, '__dict__'):
                    logger.info(f"Response attributes: {dir(response)}")
                
                if not response:
                    logger.warning("Empty response from CondApi")
                    return [{"error": "Empty response from Cond API"}]
                
                if not hasattr(response, 'results'):
                    logger.warning(f"No 'results' attribute in response: {response}")
                    # Attempt to access response as dictionary
                    if hasattr(response, 'to_dict'):
                        response_dict = response.to_dict()
                        logger.info(f"Response as dict: {response_dict}")
                        if 'results' in response_dict:
                            response_results = response_dict['results']
                        else:
                            logger.warning("No results field in response dictionary")
                            return [{"error": "Unexpected API response format"}]
                    else:
                        logger.warning("Response has no to_dict method")
                        return [{"error": "Unexpected API response format"}]
                else:
                    response_results = response.results
                
                logger.info(f"Found {len(response_results)} alarms")
                
                alerts = []
                for alert in response_results:
                    # Check if alert is a dictionary or object
                    if isinstance(alert, dict):
                        alert_info = {
                            "name": alert.get("name", "N/A"),
                            "severity": alert.get("severity", "N/A"),
                            "description": alert.get("description", "N/A"),
                            "created_time": alert.get("created_time", "N/A"),
                            "last_transition_time": alert.get("last_transition_time", "N/A"),
                            "acknowledged": alert.get("acknowledged", False)
                        }
                    else:
                        alert_info = {
                            "name": getattr(alert, "name", "N/A"),
                            "severity": getattr(alert, "severity", "N/A"),
                            "description": getattr(alert, "description", "N/A"),
                            "created_time": getattr(alert, "created_time", "N/A"),
                            "last_transition_time": getattr(alert, "last_transition_time", "N/A"),
                            "acknowledged": getattr(alert, "acknowledged", False)
                        }
                    
                    # Add affected object info if available
                    if isinstance(alert, dict):
                        if "affected_mo_id" in alert:
                            alert_info["affected_mo_id"] = alert["affected_mo_id"]
                        if "affected_mo_type" in alert:
                            alert_info["affected_mo_type"] = alert["affected_mo_type"]
                    else:
                        if hasattr(alert, "affected_mo_id"):
                            alert_info["affected_mo_id"] = alert.affected_mo_id
                        if hasattr(alert, "affected_mo_type"):
                            alert_info["affected_mo_type"] = alert.affected_mo_type
                    
                    alerts.append(alert_info)
                
                return alerts
                
            except Exception as e:
                logger.error(f"Error with CondApi approach: {str(e)}")
                logger.info("Falling back to direct API call...")
                
                # Fallback to direct API call
                query_params = {}
                headers = {'Accept': 'application/json'}
                api_path = '/cond/Alarms'
                
                # Make raw API call
                response = self.api_client.call_api(
                    api_path, 'GET',
                    query_params=query_params,
                    headers=headers,
                    response_type='object'
                )
                
                logger.info(f"Direct API call response type: {type(response)}")
                
                if isinstance(response, tuple):
                    data = response[0]  # First element is typically the data
                    logger.info(f"Tuple response, first element type: {type(data)}")
                else:
                    data = response
                
                # Handle potential None response or empty list
                if not data:
                    logger.warning("Empty data from direct API call")
                    return [{"error": "No data returned from direct API call"}]
                
                alerts = []
                
                # Try to process the data based on its structure
                if isinstance(data, dict):
                    if "Results" in data:
                        for alert in data.get("Results", []):
                            alert_info = {
                                "name": alert.get("Name", "N/A"),
                                "severity": alert.get("Severity", "N/A"),
                                "description": alert.get("Description", "N/A"),
                                "created_time": alert.get("CreatedTime", "N/A"),
                                "last_transition_time": alert.get("LastTransitionTime", "N/A"),
                                "acknowledged": alert.get("Acknowledged", False)
                            }
                            alerts.append(alert_info)
                    else:
                        logger.warning(f"Unexpected data structure: {data.keys()}")
                        return [{"error": f"Unexpected response format: {list(data.keys())}"}]
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "Results" in item:
                            for alert in item.get("Results", []):
                                alert_info = {
                                    "name": alert.get("Name", "N/A"),
                                    "severity": alert.get("Severity", "N/A"),
                                    "description": alert.get("Description", "N/A"),
                                    "created_time": alert.get("CreatedTime", "N/A"),
                                    "last_transition_time": alert.get("LastTransitionTime", "N/A"),
                                    "acknowledged": alert.get("Acknowledged", False)
                                }
                                alerts.append(alert_info)
                        elif isinstance(item, dict):
                            # Try to treat each item as an alert
                            alert_info = {
                                "name": item.get("Name", item.get("name", "N/A")),
                                "severity": item.get("Severity", item.get("severity", "N/A")),
                                "description": item.get("Description", item.get("description", "N/A")),
                                "created_time": item.get("CreatedTime", item.get("created_time", "N/A")),
                                "last_transition_time": item.get("LastTransitionTime", item.get("last_transition_time", "N/A")),
                                "acknowledged": item.get("Acknowledged", item.get("acknowledged", False))
                            }
                            alerts.append(alert_info)
                else:
                    logger.warning(f"Unhandled response data type: {type(data)}")
                    return [{"error": f"Unhandled response data type: {type(data)}"}]
                
                if alerts:
                    return alerts
                else:
                    return [{"error": "Could not extract alerts from response"}]
        
        except Exception as e:
            logger.error(f"Error fetching health alerts: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return [{"error": str(e)}]  # Return list instead of dict to maintain consistency
            
    def get_firmware_updates(self) -> List[Dict[str, Any]]:
        """Get list of firmware updates from Intersight."""
        try:
            api_instance = FirmwareApi(self.api_client)
            response = api_instance.get_firmware_distributable_list()
            
            firmware_updates = []
            for update in response.results:
                # Build dictionary with safe attribute access
                firmware = {}
                
                # Add attributes that are available, with safe fallbacks
                if hasattr(update, "name"):
                    firmware["name"] = update.name
                else:
                    firmware["name"] = "N/A"
                    
                if hasattr(update, "version"):
                    firmware["version"] = update.version
                else:
                    firmware["version"] = "N/A"
                    
                if hasattr(update, "bundle_type"):
                    firmware["bundle_type"] = update.bundle_type
                else:
                    firmware["bundle_type"] = "N/A"
                    
                if hasattr(update, "platform_type"):
                    firmware["platform_type"] = update.platform_type
                else:
                    firmware["platform_type"] = "N/A"
                    
                if hasattr(update, "import_state"):
                    firmware["status"] = update.import_state
                else:
                    firmware["status"] = "N/A"
                
                if hasattr(update, "created_time"):
                    firmware["created_time"] = update.created_time
                else:
                    firmware["created_time"] = "N/A"
                
                firmware_updates.append(firmware)
                
            return firmware_updates
        except Exception as e:
            return {"error": str(e)}
            
    def get_server_profiles(self) -> List[Dict[str, Any]]:
        """Get list of server profiles from Intersight."""
        try:
            # Try multiple potential API paths for server profiles
            # Different Intersight versions and configurations may use different paths
            
            # List of potential API paths to try in order
            api_paths = [
                '/profile/Profiles',             # Try profile namespace
                '/server/Profiles',              # Original path
                '/server/ProfileTemplates',      # Try profile templates
                '/server/profile/Profiles',      # Try nested namespace
                '/serverprofile/Profiles',       # Try alternative casing
                '/profiles'                      # Try simple path
            ]
            
            # Try each path in sequence until one works
            for api_path in api_paths:
                try:
                    logger.info(f"Attempting to fetch server profiles with path: {api_path}")
                    
                    # Use the proper method based on the SDK's requirements
                    response = self.api_client.call_api(
                        api_path, 'GET',
                        query_params={},
                        header_params={'Accept': 'application/json'},
                        response_type='object'
                    )
                    
                    # If we get here, the call succeeded - use this response
                    logger.info(f"Successfully retrieved profiles using path: {api_path}")
                    break
                    
                except Exception as path_error:
                    # Log the error and try the next path
                    logger.warning(f"Failed to retrieve profiles with path {api_path}: {str(path_error)}")
                    # Set a default empty response in case all paths fail
                    response = ({"Results": []}, 200, {})
            
            logger.info(f"Profile API call response type: {type(response)}")
            
            if isinstance(response, tuple):
                data = response[0]  # First element is typically the data
            else:
                data = response
            
            # Handle potential None response
            if not data:
                logger.warning("Empty data from profile API call")
                return [{"error": "No profile data returned from API"}]
            
            profiles = []
            
            # Process the data based on its structure
            if isinstance(data, dict):
                results = data.get("Results", [])
                if not results:
                    logger.warning(f"No Results field in response: {list(data.keys())}")
                    return [{"error": "No Results field in API response"}]
                
                for profile in results:
                    profile_info = {}
                    
                    # Extract fields with safe fallbacks
                    profile_info["name"] = profile.get("Name", "N/A")
                    profile_info["description"] = profile.get("Description", "N/A")
                    
                    # Handle nested organization object
                    org = profile.get("Organization", {})
                    if isinstance(org, dict) and "Name" in org:
                        profile_info["organization"] = org.get("Name", "N/A")
                    else:
                        profile_info["organization"] = "N/A"
                    
                    # Get deployment status
                    profile_info["status"] = profile.get("ConfigContext", {}).get("ConfigState", "N/A")
                    
                    # Get assigned server info
                    if "AssignedServer" in profile and isinstance(profile["AssignedServer"], dict):
                        server = profile["AssignedServer"]
                        profile_info["assigned_server"] = server.get("Name", "N/A")
                        profile_info["model"] = server.get("Model", "N/A")
                        profile_info["serial"] = server.get("Serial", "N/A")
                    else:
                        profile_info["assigned_server"] = "Not Assigned"
                        profile_info["model"] = "N/A"
                        profile_info["serial"] = "N/A"
                    
                    profiles.append(profile_info)
            
            return profiles
        except Exception as e:
            logger.error(f"Error fetching server profiles: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return [{"error": str(e)}]


# Update the original IntersightAPI class to use the new client tool and enhanced methods
class IntersightAPI:
    def __init__(self):
        try:
            self.client = IntersightClientTool()
        except Exception as e:
            logger.error(f"Error initializing Intersight API: {str(e)}")
            # Don't raise exception here, instead set a flag to indicate initialization failed
            self.initialization_failed = True
            self.error_message = str(e)
        else:
            self.initialization_failed = False
            self.error_message = None

    def query(self, question: str) -> str:
        # First check if initialization failed
        if hasattr(self, 'initialization_failed') and self.initialization_failed:
            return f"Error: Intersight API initialization failed - {self.error_message}. Please check your API credentials."
        
        try:
            # Determine query type based on keywords
            query_patterns = {
                "server": ["server", "servers", "ucs", "hardware", "compute", "blade", "rack"],
                "network": ["network", "vlan", "uplink", "connectivity", "interface"],
                "health": ["health", "alert", "status", "condition"],
                "vm": ["vm", "virtual machine", "virtualization", "hypervisor"],
                "device": ["device", "connector", "connection", "registered"],
                "firmware": ["firmware", "update", "upgrade", "software", "version"],
                "profile": ["profile", "profiles", "template", "templates", "configuration"]
            }

            # Match question to query type
            query_type = None
            for category, keywords in query_patterns.items():
                if any(keyword in question.lower() for keyword in keywords):
                    query_type = category
                    break

            if query_type == "server":
                servers = self.client.get_servers()
                if isinstance(servers, dict) and "error" in servers:
                    return f"Error fetching server information: {servers['error']}"
                return self._format_server_response(servers)

            elif query_type == "network":
                elements = self.client.get_network_elements()
                if isinstance(elements, dict) and "error" in elements:
                    return f"Error fetching network information: {elements['error']}"
                return self._format_network_response(elements)

            elif query_type == "health":
                alerts = self.client.get_health_alerts()
                if isinstance(alerts, dict) and "error" in alerts:
                    return f"Error fetching health information: {alerts['error']}"
                return self._format_health_response(alerts)
                
            elif query_type == "vm":
                vms = self.client.get_virtual_machines()
                if isinstance(vms, dict) and "error" in vms:
                    return f"Error fetching virtual machine information: {vms['error']}"
                return self._format_vm_response(vms)
                
            elif query_type == "device":
                devices = self.client.get_device_connectors()
                if isinstance(devices, dict) and "error" in devices:
                    return f"Error fetching device connector information: {devices['error']}"
                return self._format_device_response(devices)
                
            elif query_type == "firmware":
                firmware = self.client.get_firmware_updates()
                if isinstance(firmware, dict) and "error" in firmware:
                    return f"Error fetching firmware information: {firmware['error']}"
                return self._format_firmware_response(firmware)
                
            elif query_type == "profile":
                profiles = self.client.get_server_profiles()
                if isinstance(profiles, dict) and "error" in profiles:
                    return f"Error fetching profile information: {profiles['error']}"
                return self._format_profile_response(profiles)

            else:
                return "Please specify what information you'd like to know about your Cisco Intersight infrastructure (servers, network, health status, virtual machines, device connectors, firmware updates, or server profiles)."

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return f"Error processing query: {str(e)}"

    def _format_server_response(self, servers: List[Dict[str, Any]]) -> str:
        if not servers:
            return "No servers found in inventory"

        response = "## Server Inventory\n\n"
        response += "| Name | Model | Serial | Power State | Firmware |\n"
        response += "|------|--------|--------|-------------|----------|\n"

        for server in servers:
            response += f"| {server.get('name', 'N/A')} | {server.get('model', 'N/A')} | {server.get('serial', 'N/A')} | {server.get('power_state', 'N/A')} | {server.get('firmware', 'N/A')} |\n"

        return response

    def _format_network_response(self, elements: List[Dict[str, Any]]) -> str:
        if not elements:
            return "No network elements found"

        response = "## Network Elements\n\n"
        response += "| Device ID | Model | Serial | Management IP | Version |\n"
        response += "|-----------|-------|--------|---------------|----------|\n"

        for element in elements:
            response += f"| {element.get('device_id', 'N/A')} | {element.get('model', 'N/A')} | {element.get('serial', 'N/A')} | {element.get('management_ip', 'N/A')} | {element.get('version', 'N/A')} |\n"

        return response

    def _format_health_response(self, alerts: List[Dict[str, Any]]) -> str:
        # Check if there's an error message
        if len(alerts) == 1 and "error" in alerts[0]:
            error_msg = alerts[0]['error']
            
            # Create a more detailed error response
            response = "## Error Retrieving Health Alerts\n\n"
            response += f"**Error Message:** {error_msg}\n\n"
            response += "### Troubleshooting Steps:\n\n"
            response += "1. Verify that your Intersight API credentials are correct and have sufficient permissions\n"
            response += "2. Check that your Intersight account has access to view alerts and alarms\n"
            response += "3. Ensure connectivity to the Intersight API service\n"
            response += "4. Try again in a few moments as the service might be temporarily unavailable\n\n"
            response += "If the issue persists, please check the application logs for more detailed error information."
            
            return response
            
        if not alerts:
            return "No health alerts found in your environment. All systems appear to be operating normally."

        response = "## Health Alerts\n\n"
        response += "| Name | Severity | Description | Created | Status |\n"
        response += "|------|----------|-------------|---------|--------|\n"

        for alert in alerts:
            # Truncate description if too long
            description = alert.get('description', 'N/A')
            if len(description) > 50:
                description = description[:47] + "..."

            response += f"| {alert.get('name', 'N/A')} | {alert.get('severity', 'N/A')} | {description} | {alert.get('created_time', 'N/A')} | {'Acknowledged' if alert.get('acknowledged', False) else 'Active'} |\n"

        return response
        
    def _format_vm_response(self, vms: List[Dict[str, Any]]) -> str:
        if not vms:
            return "No virtual machines found"

        response = "## Virtual Machines\n\n"
        response += "| Name | Power State | Host | CPU | Memory | UUID |\n"
        response += "|------|------------|------|-----|--------|---------|\n"

        for vm in vms:
            response += f"| {vm.get('name', 'N/A')} | {vm.get('power_state', 'N/A')} | {vm.get('host_name', 'N/A')} | {vm.get('cpu', 'N/A')} | {vm.get('memory', 'N/A')} | {vm.get('uuid', 'N/A')} |\n"

        return response
        
    def _format_device_response(self, devices: List[Dict[str, Any]]) -> str:
        if not devices:
            return "No device connectors found"

        response = "## Device Connectors\n\n"
        response += "| Device Type | Platform Type | Device Hostname | Connection Status | Connection Reason |\n"
        response += "|-------------|---------------|-----------------|-------------------|-------------------|\n"

        for device in devices:
            response += f"| {device.get('device_type', 'N/A')} | {device.get('platform_type', 'N/A')} | {device.get('device_hostname', 'N/A')} | {device.get('connection_status', 'N/A')} | {device.get('connection_reason', 'N/A')} |\n"

        return response
        
    def _format_firmware_response(self, firmware: List[Dict[str, Any]]) -> str:
        if not firmware:
            return "No firmware updates found"

        response = "## Firmware Updates\n\n"
        response += "| Name | Version | Bundle Type | Platform | Status | Created |\n"
        response += "|------|---------|-------------|----------|--------|--------|\n"

        for update in firmware:
            response += f"| {update.get('name', 'N/A')} | {update.get('version', 'N/A')} | {update.get('bundle_type', 'N/A')} | {update.get('platform_type', 'N/A')} | {update.get('status', 'N/A')} | {update.get('created_time', 'N/A')} |\n"

        return response
        
    def _format_profile_response(self, profiles: List[Dict[str, Any]]) -> str:
        # Check if there's an error message
        if len(profiles) == 1 and "error" in profiles[0]:
            error_msg = profiles[0]['error']
            
            # Create a more detailed error response
            response = "## Error Retrieving Server Profiles\n\n"
            response += f"**Error Message:** {error_msg}\n\n"
            response += "### Troubleshooting Steps:\n\n"
            response += "1. Verify that your Intersight API credentials are correct and have sufficient permissions\n"
            response += "2. Check that your Intersight account has access to view server profiles\n"
            response += "3. Ensure connectivity to the Intersight API service\n"
            response += "4. Try again in a few moments as the service might be temporarily unavailable\n\n"
            response += "If the issue persists, please check the application logs for more detailed error information."
            
            return response
            
        if not profiles:
            return "No server profiles found in your environment."

        response = "## Server Profiles\n\n"
        response += "| Name | Organization | Status | Assigned Server | Model | Serial |\n"
        response += "|------|--------------|--------|-----------------|-------|--------|\n"

        for profile in profiles:
            response += f"| {profile.get('name', 'N/A')} | {profile.get('organization', 'N/A')} | {profile.get('status', 'N/A')} | {profile.get('assigned_server', 'N/A')} | {profile.get('model', 'N/A')} | {profile.get('serial', 'N/A')} |\n"

        return response
