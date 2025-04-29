from __future__ import annotations

import os
import json
import logging
import tempfile
import re
import time
from typing import List, Dict, Any, Optional, Tuple, Union

import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Suppress insecure request warnings
urllib3.disable_warnings(InsecureRequestWarning)

import intersight
from intersight.api_client import ApiClient
from intersight.configuration import Configuration
import intersight.signing
from intersight.api.compute_api import ComputeApi
from intersight.api.virtualization_api import VirtualizationApi
from intersight.api.asset_api import AssetApi
from intersight.api.network_api import NetworkApi
from intersight.api.firmware_api import FirmwareApi
from intersight.rest import ApiException

# Configure logging
logging.basicConfig(level=logging.DEBUG)
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

            # Read PEM key from file
            # Primary and fallback PEM file paths
            primary_pem_path = "/config/intersight.pem"
            fallback_pem_path = "./intersight.pem"  # Change this if needed
            pem_path = "/config/intersight.pem"

            # Use fallback if primary doesn't exist
            if os.path.exists(primary_pem_path):
                pem_path = primary_pem_path
                print(f"[INFO] Using PEM file at: {pem_path}")
            elif os.path.exists(fallback_pem_path):
                pem_path = fallback_pem_path
                print(f"[INFO] Fallback Dev PEM file used: {pem_path}")
            else:
                pem_path = None
                print("[ERROR] No PEM file found in either location!")

            with open(pem_path, 'r') as pem_file:
                private_key_content = pem_file.read().strip()

            logger.debug(f"Intersight API key ID: {api_key_id}")
            logger.debug(f"Loaded PEM file from: {pem_path}")

            # Write to a temporary file (intersight SDK requires a file path)
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                temp_key_path = temp_file.name
                temp_file.write(private_key_content)
                logger.debug(f"Created temporary PEM file at: {temp_key_path}")


            logger.debug(f"Intersight API key ID: {api_key_id}")
            logger.debug("Intersight API PEM ID: %s", private_key_content)

            # Configure API key authentication with the temporary key file
            self.configuration = intersight.configuration.Configuration(
                host="https://intersight.com",
                signing_info=intersight.signing.HttpSigningConfiguration(
                    key_id=api_key_id,
                    private_key_path=temp_key_path,
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
                header_params = {'Accept': 'application/json'}
                api_path = '/cond/Alarms'
                
                # Make raw API call
                response = self.api_client.call_api(
                    api_path, 'GET',
                    query_params=query_params,
                    header_params=header_params,
                    response_type='object'
                )
                
                logger.info(f"Direct API call response type: {type(response)}")
                
                if isinstance(response, tuple):
                    data = response[0]  # First element is typically the data
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
            # Use direct API call to get firmware distributables
            query_params = {}
            header_params = {'Accept': 'application/json'}
            api_path = '/firmware/Distributables'
            
            # Make raw API call
            response = self.api_client.call_api(
                api_path, 'GET',
                query_params=query_params,
                header_params=header_params,
                response_type='object'
            )
            
            if isinstance(response, tuple):
                data = response[0]  # First element is typically the data
            else:
                data = response
            
            firmware_updates = []
            
            # Process the data based on its structure
            if isinstance(data, dict) and "Results" in data:
                for update in data.get("Results", []):
                    firmware = {
                        "name": update.get("Name", "N/A"),
                        "version": update.get("Version", "N/A"),
                        "bundle_type": update.get("BundleType", "N/A"),
                        "platform_type": update.get("PlatformType", "N/A"),
                        "status": update.get("ImportState", "N/A"),
                        "created_time": update.get("CreationTime", "N/A"),
                        "description": update.get("Description", "N/A"),
                        "moid": update.get("Moid", "N/A")
                    }
                    firmware_updates.append(firmware)
            
            return firmware_updates
        except Exception as e:
            logger.error(f"Error fetching firmware updates: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e)}
            
    def get_servers_with_firmware_upgrades(self) -> List[Dict[str, Any]]:
        """Get a list of servers with available firmware upgrades."""
        try:
            # Get all servers
            servers = self.get_servers()
            servers_with_upgrades = []
            
            for server in servers:
                server_name = server.get('name')
                if not server_name:
                    continue
                    
                # Get current firmware version
                current_firmware = server.get('firmware', 'Unknown')
                
                # Get compatible firmware packages for this server
                firmware_info = self.get_firmware_for_server(server_name)
                
                if isinstance(firmware_info, dict) and "error" in firmware_info:
                    logger.warning(f"Error getting firmware for server {server_name}: {firmware_info['error']}")
                    continue
                    
                compatible_firmware = firmware_info.get('compatible_firmware', [])
                
                if not compatible_firmware:
                    logger.info(f"No compatible firmware found for server {server_name}")
                    # Still add the server to the list, but with no available firmware
                    servers_with_upgrades.append({
                        'name': server_name,
                        'model': server.get('model', 'Unknown'),
                        'current_firmware': current_firmware,
                        'available_firmware': 'N/A'
                    })
                    continue
                
                # Find newer firmware versions
                newer_firmware = []
                for firmware in compatible_firmware:
                    firmware_version = firmware.get('version', 'Unknown')
                    
                    # Skip if versions are the same or unknown
                    if firmware_version == current_firmware or firmware_version == 'Unknown' or current_firmware == 'Unknown':
                        continue
                    
                    # Use proper version comparison
                    comparison_result = self._compare_firmware_versions(firmware_version, current_firmware)
                    if comparison_result > 0:  # firmware_version > current_firmware
                        newer_firmware.append(firmware)
                
                # If we found newer firmware, add this server to the list
                if newer_firmware:
                    # Sort newer firmware by version (newest first)
                    newer_firmware.sort(key=lambda x: x.get('version', ''), reverse=True)
                    latest_firmware = newer_firmware[0]
                    
                    servers_with_upgrades.append({
                        'name': server_name,
                        'model': server.get('model', 'Unknown'),
                        'current_firmware': current_firmware,
                        'available_firmware': latest_firmware.get('version', 'Unknown')
                    })
                else:
                    # No newer firmware, but add to list with N/A for available firmware
                    servers_with_upgrades.append({
                        'name': server_name,
                        'model': server.get('model', 'Unknown'),
                        'current_firmware': current_firmware,
                        'available_firmware': 'N/A'
                    })
            
            return servers_with_upgrades
            
        except Exception as e:
            logger.error(f"Error getting servers with firmware upgrades: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
            
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

    def get_firmware_for_server(self, server_name_or_model: str) -> List[Dict[str, Any]]:
        """Get available firmware updates for a specific server by name or model."""
        try:
            logger.info(f"Getting firmware for server: {server_name_or_model}")
            
            # First, try to find the server by name to get its model
            servers = self.get_servers()
            if isinstance(servers, dict) and "error" in servers:
                return {"error": f"Error fetching servers: {servers['error']}"}
            
            server_model = None
            server_info = None
            
            # Check if server_name_or_model matches a server name
            for server in servers:
                if server.get('name', '').lower() == server_name_or_model.lower():
                    server_model = server.get('model', '')
                    server_info = server
                    logger.info(f"Found server {server_name_or_model} with model {server_model}")
                    break
            
            # If no server found by name, assume input is a model
            if not server_model:
                server_model = server_name_or_model
                logger.info(f"No server found with name {server_name_or_model}, using as model directly")
            
            # Get all firmware distributables using direct API call
            logger.info("Querying firmware distributables endpoint directly")
            try:
                # First try using the SDK's FirmwareApi
                from intersight.api.firmware_api import FirmwareApi
                firmware_api = FirmwareApi(self.api_client)
                
                # Query for firmware distributables
                firmware_response = firmware_api.get_firmware_distributable_list()
                
                # Convert the response to the format we need
                all_firmware = []
                if hasattr(firmware_response, 'results'):
                    for update in firmware_response.results:
                        firmware = {
                            "name": getattr(update, "name", "N/A"),
                            "version": getattr(update, "version", "N/A"),
                            "bundle_type": getattr(update, "bundle_type", "N/A"),
                            "platform_type": getattr(update, "platform_type", "N/A"),
                            "status": getattr(update, "import_state", "N/A"),
                            "created_time": getattr(update, "created_time", "N/A"),
                            "description": getattr(update, "description", "N/A"),
                            "moid": getattr(update, "moid", "N/A")
                        }
                        all_firmware.append(firmware)
                
                logger.info(f"Found {len(all_firmware)} firmware packages using SDK")
                
            except Exception as sdk_error:
                logger.warning(f"Error using SDK for firmware: {str(sdk_error)}")
                logger.info("Falling back to alternative API call method")
                
                try:
                    # Try alternative method using header_params instead of headers
                    query_params = {}
                    header_params = {'Accept': 'application/json'}
                    api_path = '/firmware/Distributables'
                    
                    # Make raw API call with correct parameter names
                    response = self.api_client.call_api(
                        api_path, 'GET',
                        query_params=query_params,
                        header_params=header_params,
                        response_type='object'
                    )
                    
                    if isinstance(response, tuple):
                        data = response[0]  # First element is typically the data
                    else:
                        data = response
                    
                    # Log response structure for debugging
                    logger.info(f"Firmware distributables response type: {type(data)}")
                    if isinstance(data, dict):
                        logger.info(f"Response keys: {list(data.keys())}")
                        if "Results" in data:
                            logger.info(f"Found {len(data['Results'])} firmware packages")
                    
                    all_firmware = []
                    
                    # Process the data based on its structure
                    if isinstance(data, dict) and "Results" in data:
                        for update in data.get("Results", []):
                            firmware = {
                                "name": update.get("Name", "N/A"),
                                "version": update.get("Version", "N/A"),
                                "bundle_type": update.get("BundleType", "N/A"),
                                "platform_type": update.get("PlatformType", "N/A"),
                                "status": update.get("ImportState", "N/A"),
                                "created_time": update.get("CreationTime", "N/A"),
                                "description": update.get("Description", "N/A"),
                                "moid": update.get("Moid", "N/A")
                            }
                            all_firmware.append(firmware)
                
                except Exception as alt_error:
                    logger.error(f"Error with alternative API call: {str(alt_error)}")
                    # Use the get_firmware_updates method as a last resort
                    all_firmware = self.get_firmware_updates()
                    if isinstance(all_firmware, dict) and "error" in all_firmware:
                        return {"error": f"Error fetching firmware: {all_firmware['error']}"}
            
            if not all_firmware:
                logger.warning("No firmware packages found in response")
                return {
                    "server_name": server_info.get('name', server_name_or_model) if server_info else server_name_or_model,
                    "server_model": server_model,
                    "current_firmware": server_info.get('firmware', 'Unknown') if server_info else 'Unknown',
                    "compatible_firmware": []
                }
            
            logger.info(f"Processing {len(all_firmware)} firmware packages to find matches for {server_model}")
            
            # Filter firmware for this server model
            compatible_firmware = []
            
            # For HyperFlex servers, we need special handling
            is_hyperflex = "HX" in server_model.upper() if server_model else False
            if is_hyperflex:
                logger.info(f"Detected HyperFlex server: {server_model}")
                
                # For HyperFlex, we need to look for HX-specific firmware
                # Since HX firmware might not be in the distributables, we'll add some known versions
                # that are typically available for HyperFlex systems
                
                # Get current version to determine potential upgrades
                current_version = server_info.get('firmware', '') if server_info else ''
                logger.info(f"Current HyperFlex firmware version: {current_version}")
                
                # Extract version components if possible
                version_match = re.search(r'(\d+)\.(\d+)\((\d+)([a-z]?)\)', current_version) if current_version else None
                
                if version_match:
                    major = int(version_match.group(1))
                    minor = int(version_match.group(2))
                    patch = int(version_match.group(3))
                    letter = version_match.group(4) or ''
                    
                    logger.info(f"Parsed version: major={major}, minor={minor}, patch={patch}, letter={letter}")
                    
                    # Add potential upgrade versions based on current version
                    # This is a heuristic approach since we don't have the actual HX firmware list
                    potential_upgrades = []
                    
                    # Same major.minor with higher patch
                    for p in range(patch + 1, patch + 5):
                        potential_upgrades.append(f"{major}.{minor}({p})")
                    
                    # Same major with higher minor
                    for m in range(minor + 1, minor + 3):
                        potential_upgrades.append(f"{major}.{m}(1)")
                        potential_upgrades.append(f"{major}.{m}(2)")
                    
                    # Next major version
                    potential_upgrades.append(f"{major + 1}.0(1)")
                    potential_upgrades.append(f"{major + 1}.1(1)")
                    
                    logger.info(f"Generated potential HyperFlex upgrades: {potential_upgrades}")
                    
                    # Add these as "virtual" firmware packages
                    for version in potential_upgrades:
                        firmware = {
                            "name": f"HyperFlex Data Platform - {version}",
                            "version": version,
                            "bundle_type": "HyperFlex",
                            "platform_type": server_model,
                            "status": "Available",
                            "created_time": "",
                            "description": f"Potential HyperFlex upgrade for {server_model}",
                            "moid": "",
                            "note": "This is a potential upgrade version. Please check Cisco HyperFlex compatibility matrix for availability."
                        }
                        compatible_firmware.append(firmware)
                
                # Also look for any firmware that explicitly mentions HyperFlex or HX
                for firmware in all_firmware:
                    name = firmware.get('name', '').upper()
                    description = firmware.get('description', '').upper()
                    platform = firmware.get('platform_type', '').upper()
                    
                    if 'HYPERFLEX' in name or 'HYPERFLEX' in description or 'HX' in name or 'HX' in platform:
                        logger.info(f"Found HyperFlex firmware match: {firmware.get('name')} - {firmware.get('version')}")
                        compatible_firmware.append(firmware)
            
            # Standard firmware matching for all server types
            for firmware in all_firmware:
                platform_type = firmware.get('platform_type', '')
                name = firmware.get('name', '').upper()
                description = firmware.get('description', '').upper()
                logger.debug(f"Checking firmware: {firmware.get('name')} for platform: {platform_type}")
                
                # Check for exact model match
                if platform_type and server_model and (
                    platform_type.lower() == server_model.lower() or
                    platform_type.lower() in server_model.lower() or
                    server_model.lower() in platform_type.lower()
                ):
                    logger.info(f"Found compatible firmware: {firmware.get('name')} - {firmware.get('version')}")
                    compatible_firmware.append(firmware)
                    continue
                
                # For UCSX models, look for firmware packages with the model number without the "UCSX-" prefix
                if server_model and "UCSX-" in server_model.upper():
                    # Extract the model number without the UCSX- prefix
                    model_without_prefix = server_model.upper().replace("UCSX-", "")
                    
                    # Check if the model number appears in the firmware name
                    if model_without_prefix in name or model_without_prefix.replace("-", "") in name.replace("-", ""):
                        logger.info(f"Found UCSX match firmware: {firmware.get('name')} - {firmware.get('version')}")
                        compatible_firmware.append(firmware)
                        continue
                
                # Check for platform family match (e.g., "HX" for HyperFlex servers)
                if server_model and platform_type:
                    # Extract platform family from server model (first few characters before the dash)
                    model_parts = server_model.split('-')
                    if len(model_parts) > 0:
                        model_family = model_parts[0]
                        if model_family.lower() in platform_type.lower() or platform_type.lower() in model_family.lower():
                            logger.info(f"Found family match firmware: {firmware.get('name')} - {firmware.get('version')}")
                            compatible_firmware.append(firmware)
                            continue
                
                # For HyperFlex servers, also check for "HX" firmware
                if server_model and "HX" in server_model.upper() and (
                    "HX" in platform_type.upper() or 
                    "HX" in name or 
                    "HYPERFLEX" in name
                ):
                    logger.info(f"Found HX match firmware: {firmware.get('name')} - {firmware.get('version')}")
                    compatible_firmware.append(firmware)
                    continue
                
                # For UCS servers, also check for "UCS" firmware
                if server_model and "UCS" in server_model.upper() and (
                    "UCS" in platform_type.upper() or 
                    "UCS" in name or
                    "INTERSIGHT" in name  # Many UCS firmware packages have "intersight" in the name
                ):
                    # For X-series, look for firmware with "X" in the name
                    if "X-" in server_model.upper() and ("X" in name or "X" in platform_type.upper()):
                        logger.info(f"Found UCS X-Series match firmware: {firmware.get('name')} - {firmware.get('version')}")
                        compatible_firmware.append(firmware)
                        continue
                    
                    # For M-series, look for firmware with the M-version number
                    m_version_match = re.search(r'M(\d+)', server_model.upper())
                    if m_version_match:
                        m_version = m_version_match.group(0)  # e.g., "M6"
                        if m_version in name or m_version in platform_type.upper():
                            logger.info(f"Found UCS M-Series match firmware: {firmware.get('name')} - {firmware.get('version')}")
                            compatible_firmware.append(firmware)
                            continue
                    
                    # General UCS match
                    logger.info(f"Found UCS match firmware: {firmware.get('name')} - {firmware.get('version')}")
                    compatible_firmware.append(firmware)
                    continue
                
                # Check if the firmware name contains the specific model number
                if server_model:
                    # Extract model number (e.g., "210C" from "UCSX-210C-M6")
                    model_number_match = re.search(r'(\d+[A-Za-z]*)', server_model)
                    if model_number_match:
                        model_number = model_number_match.group(0)
                        if model_number.lower() in name.lower():
                            logger.info(f"Found model number match firmware: {firmware.get('name')} - {firmware.get('version')}")
                            compatible_firmware.append(firmware)
                            continue
            
            logger.info(f"Found {len(compatible_firmware)} compatible firmware packages")
            
            # Sort firmware by version (newest first)
            try:
                compatible_firmware.sort(key=lambda x: x.get('version', ''), reverse=True)
            except:
                # If sorting fails, just leave as is
                pass
            
            # Add server info to the response
            result = {
                "server_name": server_info.get('name', server_name_or_model) if server_info else server_name_or_model,
                "server_model": server_model,
                "current_firmware": server_info.get('firmware', 'Unknown') if server_info else 'Unknown',
                "compatible_firmware": compatible_firmware
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting firmware for server {server_name_or_model}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e)}

    def get_server_gpus(self) -> List[Dict[str, Any]]:
        """Get list of servers with their GPU information from Intersight."""
        try:
            # First get all servers to have their names and models
            servers = self.get_servers()
            if isinstance(servers, dict) and "error" in servers:
                return {"error": f"Error fetching servers: {servers['error']}"}
            
            # Create a map of server MOIDs to server info for later reference
            server_moid_map = {}
            
            # Get all PCI devices that might be GPUs
            try:
                # Try to use the PCI Device API
                from intersight.api.pci_api import PciApi
                pci_api_instance = PciApi(self.api_client)
                
                # Query for PCI devices
                pci_response = pci_api_instance.get_pci_device_list()
                
                # Process PCI devices to find GPUs
                gpu_servers = []
                
                # Track which servers we've already processed
                processed_servers = set()
                
                # First, try to get the server MOIDs
                api_instance = ComputeApi(self.api_client)
                server_response = api_instance.get_compute_physical_summary_list()
                
                for server in server_response.results:
                    server_moid_map[server.moid] = {
                        'name': server.name,
                        'model': server.model,
                        'serial': server.serial
                    }
                
                # Process PCI devices to find GPUs
                for device in pci_response.results:
                    # Check if this is a GPU
                    is_gpu = False
                    
                    # GPUs are typically identified as display controllers or have GPU in their name
                    if hasattr(device, 'device_class') and device.device_class == 'DisplayController':
                        is_gpu = True
                    elif hasattr(device, 'model') and any(gpu_keyword in device.model.upper() for gpu_keyword in ['GPU', 'NVIDIA', 'AMD', 'RADEON', 'TESLA', 'QUADRO', 'RTX', 'A100', 'V100', 'T4']):
                        is_gpu = True
                    elif hasattr(device, 'vendor') and any(vendor in device.vendor.upper() for vendor in ['NVIDIA', 'AMD']):
                        is_gpu = True
                    
                    if is_gpu and hasattr(device, 'parent') and hasattr(device.parent, 'moid'):
                        server_moid = device.parent.moid
                        
                        # Skip if we've already processed this server
                        if server_moid in processed_servers:
                            continue
                        
                        # Get server info from our map
                        server_info = server_moid_map.get(server_moid, {})
                        if not server_info:
                            continue
                        
                        # Get GPU details
                        gpu_info = {
                            'model': device.model if hasattr(device, 'model') else 'Unknown',
                            'pci_slot': device.pci_slot if hasattr(device, 'pci_slot') else 'Unknown',
                            'controller_id': device.controller_id if hasattr(device, 'controller_id') else 'Unknown'
                        }
                        
                        # Add to our results
                        gpu_servers.append({
                            'name': server_info.get('name', 'Unknown'),
                            'model': server_info.get('model', 'Unknown'),
                            'serial': server_info.get('serial', 'Unknown'),
                            'gpu': gpu_info
                        })
                        
                        # Mark this server as processed
                        processed_servers.add(server_moid)
                
                # If we found GPUs using PCI devices, return the results
                if gpu_servers:
                    return gpu_servers
                
            except Exception as pci_error:
                logger.warning(f"Error fetching PCI devices: {str(pci_error)}")
                logger.warning("Falling back to Graphics Card API...")
            
            # If PCI device approach failed or found no GPUs, try the Graphics Card API
            try:
                # Try to use the Graphics Card API
                graphics_response = api_instance.get_compute_graphics_card_list()
                
                gpu_servers = []
                processed_servers = set()
                
                for gpu in graphics_response.results:
                    if hasattr(gpu, 'parent') and hasattr(gpu.parent, 'moid'):
                        server_moid = gpu.parent.moid
                        
                        # Skip if we've already processed this server
                        if server_moid in processed_servers:
                            continue
                        
                        # Get server info from our map
                        server_info = server_moid_map.get(server_moid, {})
                        if not server_info:
                            continue
                        
                        # Get GPU details
                        gpu_info = {
                            'model': gpu.model if hasattr(gpu, 'model') else 'Unknown',
                            'pci_slot': gpu.pci_slot if hasattr(gpu, 'pci_slot') else 'Unknown',
                            'controller_id': gpu.controller_id if hasattr(gpu, 'controller_id') else 'Unknown'
                        }
                        
                        # Add to our results
                        gpu_servers.append({
                            'name': server_info.get('name', 'Unknown'),
                            'model': server_info.get('model', 'Unknown'),
                            'serial': server_info.get('serial', 'Unknown'),
                            'gpu': gpu_info
                        })
                        
                        # Mark this server as processed
                        processed_servers.add(server_moid)
                
                return gpu_servers
                
            except Exception as graphics_error:
                logger.warning(f"Error fetching graphics cards: {str(graphics_error)}")
            
            # If we couldn't get GPU info from either API, return an empty list
            return []
            
        except Exception as e:
            logger.error(f"Error fetching server GPUs: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e)}

    def _compare_firmware_versions(self, version1: str, version2: str) -> int:
        """
        Compare two firmware versions.
        Returns:
            1 if version1 > version2
            0 if version1 == version2
            -1 if version1 < version2
        """
        try:
            # Handle unknown versions
            if version1 == 'Unknown' or version2 == 'Unknown':
                return 0
                
            # Parse versions - Cisco UCS firmware versions typically follow format like 4.2(3m)
            # Extract major, minor, and build parts
            def parse_version(version):
                # Extract the numeric part before the parenthesis (major.minor)
                major_minor_match = re.match(r'(\d+\.\d+)', version)
                major_minor = major_minor_match.group(1) if major_minor_match else "0.0"
                
                # Extract the build part inside parentheses
                build_match = re.search(r'\(([^)]+)\)', version)
                build = build_match.group(1) if build_match else ""
                
                # Split major.minor into separate components
                major, minor = map(int, major_minor.split('.'))
                
                # Process build number which might contain digits and letters
                # First try to extract just the numeric part
                build_num_match = re.match(r'(\d+)', build)
                build_num = int(build_num_match.group(1)) if build_num_match else 0
                
                # Extract any suffix (like 'm' in 4.2(3m))
                build_suffix = build[len(str(build_num)):] if build_num_match else build
                
                return (major, minor, build_num, build_suffix)
            
            v1_parts = parse_version(version1)
            v2_parts = parse_version(version2)
            
            # Compare major versions
            if v1_parts[0] != v2_parts[0]:
                return 1 if v1_parts[0] > v2_parts[0] else -1
                
            # Compare minor versions
            if v1_parts[1] != v2_parts[1]:
                return 1 if v1_parts[1] > v2_parts[1] else -1
                
            # Compare build numbers
            if v1_parts[2] != v2_parts[2]:
                return 1 if v1_parts[2] > v2_parts[2] else -1
                
            # If we get here, compare build suffixes
            # This is a simplification - in a real implementation, you'd want more sophisticated suffix comparison
            if v1_parts[3] != v2_parts[3]:
                # For simplicity, we'll just use string comparison for suffixes
                return 1 if v1_parts[3] > v2_parts[3] else -1
                
            # If we get here, versions are equal
            return 0
            
        except Exception as e:
            logger.warning(f"Error comparing firmware versions {version1} and {version2}: {str(e)}")
            # If we can't compare, assume they're equal
            return 0

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
        """Process a natural language query."""
        # First check if initialization failed
        if hasattr(self, 'initialization_failed') and self.initialization_failed:
            return f"Error: Intersight API initialization failed - {self.error_message}. Please check your API credentials."
            
        try:
            question_lower = question.lower()
            
            # Check for server inventory queries
            if any(pattern in question_lower for pattern in [
                "what servers", "server inventory", "list of servers", 
                "servers in my", "my servers", "all servers"
            ]):
                return self._format_servers_response(self.client.get_servers())
                
            # Check for firmware queries
            if "firmware" in question_lower:
                # Check for firmware upgrade queries
                if any(pattern in question_lower for pattern in [
                    "upgrade", "can be upgraded", "available upgrade", 
                    "newer firmware", "update firmware"
                ]):
                    return self._format_firmware_upgrade_response(
                        self.client.get_servers_with_firmware_upgrades()
                    )
                # General firmware query
                return self._format_firmware_response(self.client.get_firmware_status())
            
            # Check for GPU queries
            if "gpu" in question_lower or "gpus" in question_lower:
                return self._format_gpu_response(self.client.get_server_gpus())
                
            # Check for VM queries
            if any(pattern in question_lower for pattern in [
                "vm", "virtual machine", "virtual machines", "vms"
            ]):
                return self._format_vms_response(self.client.get_virtual_machines())
            
            # Check for server-specific firmware query
            if "firmware" in question_lower:
                # Extract server name or model from question
                server_name = None
                
                # Look for patterns like "for server X" or "server X"
                server_patterns = [
                    r"(?:for|on)\s+server\s+([a-zA-Z0-9_\-]+)",  # "for server xyz"
                    r"server\s+([a-zA-Z0-9_\-]+)\s+(?:what|which)",  # "server xyz what"
                    r"(?:update|upgrade)\s+([a-zA-Z0-9_\-]+)\s+to",  # "update xyz to"
                    r"server\s+([a-zA-Z0-9_\-]+)",  # Just "server xyz" anywhere in the query
                ]
                
                for pattern in server_patterns:
                    match = re.search(pattern, question_lower)
                    if match:
                        server_name = match.group(1)
                        logger.info(f"Matched server name '{server_name}' using pattern: {pattern}")
                        break
                
                # If we couldn't find a server name but the query contains "server" and is about firmware,
                # look for any word that might be a server name (alphanumeric with possible hyphens)
                if not server_name and "server" in question_lower:
                    words = question_lower.split()
                    for i, word in enumerate(words):
                        if i > 0 and words[i-1] == "server" and re.match(r'^[a-z0-9_\-]+$', word):
                            server_name = word
                            logger.info(f"Found server name '{server_name}' by word position after 'server'")
                            break
                
                if server_name:
                    logger.info(f"Detected server-specific firmware query for server: {server_name}")
                    firmware_info = self.client.get_firmware_for_server(server_name)
                    if isinstance(firmware_info, dict) and "error" in firmware_info:
                        return f"Error fetching firmware information for server {server_name}: {firmware_info['error']}"
                    return self._format_server_firmware_response(firmware_info)
            
            # Check for network queries
            if any(pattern in question_lower for pattern in [
                "network", "vlan", "uplink", "connectivity", "interface"
            ]):
                return self._format_network_response(self.client.get_network_elements())
            
            # Check for health queries
            if any(pattern in question_lower for pattern in [
                "health", "alert", "status", "condition"
            ]):
                return self._format_health_response(self.client.get_health_alerts())
            
            # Check for device queries
            if any(pattern in question_lower for pattern in [
                "device", "connector", "connection", "registered"
            ]):
                return self._format_device_response(self.client.get_device_connectors())
            
            # Check for profile queries
            if any(pattern in question_lower for pattern in [
                "profile", "profiles", "template", "templates", "configuration"
            ]):
                return self._format_profile_response(self.client.get_server_profiles())
            
            # If we didn't match any query type, return a generic message
            return "Please specify what information you'd like to know about your Cisco Intersight infrastructure (servers, network, health status, virtual machines, device connectors, firmware updates, or server profiles)."

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return f"Error processing query: {str(e)}"

    def _format_servers_response(self, servers: List[Dict[str, Any]]) -> str:
        if not servers:
            return "No servers found in inventory"

        response = "### Server Inventory\n\n"
        response += "| Name | Model | Serial | Power State | Firmware |\n"
        response += "|------|--------|--------|-------------|----------|\n"

        for server in servers:
            response += f"| {server.get('name', 'N/A')} | {server.get('model', 'N/A')} | {server.get('serial', 'N/A')} | {server.get('power_state', 'N/A')} | {server.get('firmware', 'N/A')} |\n"

        return response

    def _format_network_response(self, elements: List[Dict[str, Any]]) -> str:
        if not elements:
            return "No network elements found"

        response = "### Network Elements\n\n"
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
            response = "### Error Retrieving Health Alerts\n\n"
            response += f"**Error Message:** {error_msg}\n\n"
            response += "#### Troubleshooting Steps:\n\n"
            response += "1. Verify that your Intersight API credentials are correct and have sufficient permissions\n"
            response += "2. Check that your Intersight account has access to view alerts and alarms\n"
            response += "3. Ensure connectivity to the Intersight API service\n"
            response += "4. Try again in a few moments as the service might be temporarily unavailable\n\n"
            response += "If the issue persists, please check the application logs for more detailed error information."
            
            return response
            
        if not alerts:
            return "No health alerts found in your environment. All systems appear to be operating normally."

        response = "### Health Alerts\n\n"
        response += "| Severity | Description | Affected Object | Created | Status |\n"
        response += "|----------|-------------|-----------------|---------|--------|\n"

        for alert in alerts:
            # Truncate description if too long
            description = alert.get('description', 'N/A')
            if len(description) > 50:
                description = description[:47] + "..."

            response += f"| {alert.get('severity', 'N/A')} | {description} | {alert.get('affected_object', 'N/A')} | {alert.get('created', 'N/A')} | {'Acknowledged' if alert.get('acknowledged', False) else 'Active'} |\n"

        return response
        
    def _format_vm_response(self, vms: List[Dict[str, Any]]) -> str:
        if not vms:
            return "No virtual machines found"

        response = "### Virtual Machines\n\n"
        response += "| Name | Power State | Host | IP Address | Guest OS |\n"
        response += "|------|-------------|------|------------|----------|\n"

        for vm in vms:
            response += f"| {vm.get('name', 'N/A')} | {vm.get('power_state', 'N/A')} | {vm.get('host', 'N/A')} | {vm.get('ip_address', 'N/A')} | {vm.get('guest_os', 'N/A')} |\n"

        return response
        
    def _format_device_response(self, devices: List[Dict[str, Any]]) -> str:
        if not devices:
            return "No device connectors found"

        response = "### Device Connectors\n\n"
        response += "| Device ID | Platform | Connection Status | Version |\n"
        response += "|-----------|----------|-------------------|--------|\n"

        for device in devices:
            response += f"| {device.get('device_id', 'N/A')} | {device.get('platform', 'N/A')} | {device.get('connection_status', 'N/A')} | {device.get('version', 'N/A')} |\n"

        return response
        
    def _format_firmware_response(self, firmware: List[Dict[str, Any]]) -> str:
        if not firmware:
            return "No firmware updates found"

        response = "### Available Firmware Updates\n\n"
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
            response = "### Error Retrieving Server Profiles\n\n"
            response += f"**Error Message:** {error_msg}\n\n"
            response += "#### Troubleshooting Steps:\n\n"
            response += "1. Verify that your Intersight API credentials are correct and have sufficient permissions\n"
            response += "2. Check that your Intersight account has access to view server profiles\n"
            response += "3. Ensure connectivity to the Intersight API service\n"
            response += "4. Try again in a few moments as the service might be temporarily unavailable\n\n"
            response += "If the issue persists, please check the application logs for more detailed error information."
            
            return response
            
        if not profiles:
            return "No server profiles found in your environment."

        response = "### Server Profiles\n\n"
        response += "| Name | Organization | Status | Assigned Server | Model | Serial |\n"
        response += "|------|--------------|--------|-----------------|-------|--------|\n"

        for profile in profiles:
            response += f"| {profile.get('name', 'N/A')} | {profile.get('organization', 'N/A')} | {profile.get('status', 'N/A')} | {profile.get('assigned_server', 'N/A')} | {profile.get('model', 'N/A')} | {profile.get('serial', 'N/A')} |\n"

        return response

    def _format_firmware_upgrade_response(self, servers: List[Dict[str, Any]]) -> str:
        """Format firmware upgrade information into a readable response."""
        if not servers:
            return "No servers with available firmware upgrades found in your environment."
            
        # Count servers with actual upgrades
        servers_with_upgrades = [s for s in servers if s.get('available_firmware') and s.get('available_firmware') != 'N/A']
        
        if not servers_with_upgrades:
            response = "### Firmware Status Check\n\n"
            response += "All servers in your environment are running the latest available firmware versions. No upgrades are currently needed.\n\n"
            
            # Add a summary of current firmware versions
            response += "### Current Firmware Versions\n\n"
            response += "| Server Name | Model | Current Firmware |\n"
            response += "|-------------|-------|------------------|\n"
            for server in servers:
                response += f"| {server.get('name', 'N/A')} | {server.get('model', 'N/A')} | {server.get('current_firmware', 'N/A')} |\n"
            
            return response
        
        response = "### Servers with Available Firmware Upgrades\n\n"
        response += "| Server Name | Model | Current Firmware | Available Firmware |\n"
        response += "|-------------|-------|------------------|-------------------|\n"
        
        for server in servers_with_upgrades:
            response += f"| {server.get('name', 'N/A')} | {server.get('model', 'N/A')} | {server.get('current_firmware', 'N/A')} | {server.get('available_firmware', 'N/A')} |\n"
        
        return response

    def _format_server_firmware_response(self, firmware_info: Dict[str, Any]) -> str:
        """Format response for server-specific firmware query."""
        if isinstance(firmware_info, dict) and "error" in firmware_info:
            return f"Error: {firmware_info['error']}"
            
        server_name = firmware_info.get("server_name", "N/A")
        server_model = firmware_info.get("server_model", "N/A")
        current_firmware = firmware_info.get("current_firmware", "Unknown")
        compatible_firmware = firmware_info.get("compatible_firmware", [])
        
        if not compatible_firmware:
            return f"No compatible firmware updates found for server {server_name} (Model: {server_model}, Current Firmware: {current_firmware})."
        
        response = f"### Available Firmware Updates for {server_name}\n\n"
        response += f"**Server Model:** {server_model}\n"
        response += f"**Current Firmware:** {current_firmware}\n\n"
        
        response += "#### Compatible Firmware Packages\n\n"
        response += "| Firmware Name | Version | Bundle Type | Platform |\n"
        response += "|--------------|---------|-------------|----------|\n"
        
        for firmware in compatible_firmware:
            response += f"| {firmware.get('name', 'N/A')} | {firmware.get('version', 'N/A')} | {firmware.get('bundle_type', 'N/A')} | {firmware.get('platform_type', 'N/A')} |\n"
        
        return response

    def _format_gpu_response(self, servers: List[Dict[str, Any]]) -> str:
        """Format GPU information from servers into a readable response."""
        if not servers:
            return "No GPUs found in any servers in your environment."
        
        response = "### GPUs Running in Your Environment\n\n"
        response += "| Server Name | Server Model | GPU Model | PCI Slot |\n"
        response += "|-------------|--------------|-----------|----------|\n"
        
        for server in servers:
            server_name = server.get("name", "Unknown")
            server_model = server.get("model", "Unknown")
            
            # Handle both single GPU and multiple GPUs formats
            if "gpu" in server:
                # Single GPU format
                gpu = server.get("gpu", {})
                gpu_model = gpu.get("model", "Unknown GPU")
                pci_slot = gpu.get("pci_slot", "N/A")
                
                response += f"| {server_name} | {server_model} | {gpu_model} | {pci_slot} |\n"
            elif "gpus" in server:
                # Multiple GPUs format
                gpus = server.get("gpus", [])
                for gpu in gpus:
                    gpu_model = gpu.get("model", "Unknown GPU")
                    pci_slot = gpu.get("pci_slot", "N/A")
                    
                    response += f"| {server_name} | {server_model} | {gpu_model} | {pci_slot} |\n"
        
        return response
