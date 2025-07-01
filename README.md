# Cisco Bridgy AI Assistant

![Cisco Bridgy Logo](/image.png)
 
[![OpenShift](https://img.shields.io/badge/openshift-deployment-red?style=flat-square&logo=redhat)](https://www.openshift.com/)
[![Python Version](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-TBD-yellow.svg)](#license)

## Overview

Cisco Bridgy is an advanced AI assistant designed to provide specialized expertise in Cisco infrastructure, focusing on Intersight, Nexus Dashboard, AI Pods, and general Cisco knowledge. Utilizing a sophisticated "Mix of Experts" model, the assistant routes queries to specialized knowledge domains for precise and context-aware responses.

## Key Features

- **Multi-Expert Routing**:
  - Intersight Expert: Server inventory and infrastructure management
  - Nexus Dashboard Expert: Network fabric management and device monitoring
  - AI Pods Expert: AI infrastructure and hardware insights
  - General Expert: Handles general Cisco knowledge questions

- **Nexus Dashboard Integration**:
  - Fabric management and inventory
  - MSD (Multi-Site Domain) fabric associations
  - Device/switch inventory from NDFC
  - External IP configuration for trap and syslog

- **Intersight Integration**:
  - Server inventory and management
  - Infrastructure monitoring
  - Hardware details and specifications

- **Advanced Technology Stack**:
  - Remote LLM Integration with Meta-Llama-3-8B-Instruct
  - LangChain Integration
  - Streamlit-based Web Interface

## System Requirements

### Deployment Environment
- **OpenShift Container Platform**: Version 4.x or higher
- **GPU-enabled Node**: Nvidia GPU with minimum 18 GB VRAM

### Hardware Requirements
- **GPU**: Nvidia GPU with CUDA support
- **CUDA**: Version 12.x
- **cuDNN**: Version 9+

### Software Prerequisites
- Intersight API Key & PEM file (for Intersight integration)
- Nexus Dashboard credentials (for Nexus Dashboard functionality)
- LangSmith Key (Optional, for troubleshooting)

## OpenShift Deployment

The Bridgy AI Assistant is designed to be deployed exclusively on OpenShift, leveraging GPU resources for optimal performance.

### Deployment Overview

1. **OpenShift Deployment Resources**:
   - All necessary deployment configurations are in the `osdeploy/` directory
   - ConfigMaps contain embedded Dockerfiles and configuration files
   - Deployment configurations are set to use GPU resources

2. **Environment Configuration**:
   - Environment variables and credentials are managed through OpenShift Secrets
   - PEM files for Intersight API are mounted as volumes

### Deployment Steps

```bash
# Login to OpenShift cluster
oc login --token=<your-token> --server=<your-openshift-server>

# Create a new project (or use an existing one)
oc new-project bridgy-ai

# Apply the deployment configurations
oc apply -f osdeploy/

# Create necessary secrets
oc create secret generic bridgy-env --from-file=.env=./.env
oc create secret generic intersight-key --from-file=intersight.pem=./intersight.pem

# Verify deployment status
oc get pods
```

The application is designed to be accessed internally within the OpenShift cluster by other services and does not expose external routes.

## Configuration

Create a `.env` file with the following variables:

```
# LangSmith Configuration (Optional)
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=bridgy

# Intersight Configuration
INTERSIGHT_API_KEY=your_intersight_api_key_id

# Nexus Dashboard Configuration
NEXUS_DASHBOARD_URL=https://your-nexus-dashboard-instance
NEXUS_DASHBOARD_USERNAME=your_username
NEXUS_DASHBOARD_PASSWORD=your_password
NEXUS_DASHBOARD_DOMAIN=local  # Optional, defaults to "local"
```

### Configure Intersight API credentials

If you plan to use the Intersight Expert functionality, you'll need:
   
- Add your Intersight API Key ID to the `.env` file as shown above
- Place your Intersight Secret Key in the root directory as `intersight_secret_key.pem`
   
You can generate these credentials from your Intersight account under Settings > API Keys.

## Usage

The Bridgy AI Assistant is designed to be used as an API service within an OpenShift environment:

1. **API Integration**: Access the service via API calls to the internal service endpoint
2. **Routing**: The service automatically routes queries to the appropriate expert system
3. **Authentication**: All API calls should include appropriate authentication headers
4. **Response Handling**: The service provides JSON responses that can be integrated with frontend applications

## Verification

Verify your OpenShift deployment by checking:

```bash
# Check pod status
oc get pods -l app=bridgy-ai

# View pod logs
oc logs $(oc get pods -l app=bridgy-ai -o name | head -n 1)

# Check if the service is running
oc get services -l app=bridgy-ai

# Verify ConfigMaps are correctly applied
oc get configmaps

# Check if secrets are properly created
oc get secrets | grep bridgy
```

Ensure all pods are in the "Running" state and the logs show successful initialization with no errors.

## Troubleshooting

### Common OpenShift Deployment Issues

- **Pod Failures**:
  - Check pod logs: `oc logs <pod-name>`
  - Verify resource limits are appropriate for GPU usage
  - Ensure OpenShift has NVIDIA GPU operators installed on target nodes

- **Secret Configuration Issues**:
  - Verify secrets are correctly created: `oc describe secret <secret-name>`
  - Check secret mounting in pod configuration
  - Ensure .env file contains all required environment variables

- **Network Connectivity Issues**:
  - Verify OpenShift internal network policies allow service communication
  - Check service definitions: `oc get svc`
  - Test connectivity between pods: `oc exec <pod-name> -- curl -v <service-name>:<port>`

- **API Credential Issues**:
  - **Nexus Dashboard**: Check secret contains valid credentials and correct URL format (https://)
  - **Intersight API**: Verify API key in secrets and ensure PEM file is correctly mounted
  - **LangSmith**: Confirm API key is valid if tracing is enabled

- **GPU Resources**:
  - Verify GPU availability in cluster: `oc get nodes -o json | jq '.items[] | {name:.metadata.name, gpu:.status.capacity."nvidia.com/gpu"}'`
  - Check GPU usage in pods: `oc exec <pod-name> -- nvidia-smi`
  - Ensure pods are scheduled on GPU-enabled nodes

## Project Structure

```
├── bridgy-main/                # Main application code
│   ├── experts/                # Expert modules
│   │   ├── ai_pods_expert.py    # AI Pods expert implementation
│   │   ├── general_expert.py    # General Cisco knowledge expert
│   │   ├── intersight_expert.py # Intersight expert implementation
│   │   ├── nexus_dashboard_expert.py # Nexus Dashboard expert implementation
│   │   └── router.py            # Expert routing logic
│   ├── pdf/                    # Documentation PDFs
│   ├── tools/                  # Utility tools
│   │   ├── intersight_api.py    # Intersight API interface
│   │   ├── nexus_dashboard_api.py # Nexus Dashboard API interface
│   │   └── pdf_loader.py        # PDF document loader
│   ├── config.py               # Application configuration
│   ├── Dockerfile              # Container definition for application
│   ├── requirements.txt        # Consolidated Python dependencies with GPU support
│   └── main.py                 # Main application entry point
├── osdeploy/                   # OpenShift deployment configurations
│   ├── bridgy-main-cm1-configmap.yaml # Main ConfigMap with embedded Dockerfile
│   └── [other deployment yamls]  # Other OpenShift resources
└── entrypoint.sh               # Container entry point script
```

## Nexus Dashboard Integration

The Nexus Dashboard expert agent is specialized in handling queries related to Cisco's data center networking solutions, particularly the Nexus Dashboard platform.

### Key Capabilities

1. **Fabric Management**:
   - List and query fabrics in your Nexus environment
   - View fabric details including type, state, and configuration

2. **MSD Fabric Associations**:
   - View Multi-Site Domain fabric associations
   - Understand relationships between fabrics

3. **Device Inventory**:
   - List all switches and devices managed by NDFC
   - View device details including name, IP, serial number, model, and status

4. **Network Configuration**:
   - Retrieve external IP configuration for trap and syslog
   - Access management IP information
   
5. **Telemetry & Monitoring**:
   - Check alarm status and notifications
   - Fetch telemetry data from network devices

6. **Automation**:
   - Trigger automation workflows
   - Execute compliance checks

### API Endpoints

The Nexus Dashboard API supports the following endpoints:

- `/api/v1/sites` - Get information about sites
- `/api/v1/fabrics` - Get information about network fabrics
- `/api/v1/devices` - Get information about network devices
- `/api/v1/telemetry` - Get telemetry data
- `/api/v1/alarms` - Get alarm information
- `/api/v1/workflows` - Get and execute automation workflows
- `/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics` - Primary endpoint for fabric information
- `/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msd/fabric-associations` - MSD fabric associations
- `/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/inventory/allswitches` - Device inventory

### Usage Examples

The system automatically routes queries related to Nexus Dashboard to the Nexus Dashboard expert. Examples include:

- "What's the status of my network fabric?"
- "Show me all critical alarms in my Nexus Dashboard"
- "What devices are registered in my Nexus Dashboard?"
- "Get telemetry data for CPU utilization on my switches"
- "Execute the network compliance check workflow"

### Fallback Behavior

If the Nexus Dashboard API is unavailable, the system will automatically fall back to the General Expert, which will provide general information about Nexus Dashboard based on its training data.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| LANGSMITH_API_KEY | LangSmith API key for tracing | No |
| LANGSMITH_PROJECT | LangSmith project name | No |
| LANGSMITH_TRACING | Enable/disable tracing (true/false) | No |
| LANGSMITH_ENDPOINT | LangSmith API endpoint | No |
| INTERSIGHT_API_KEY | Your Intersight API key ID | Yes (for Intersight) |
| NEXUS_DASHBOARD_URL | URL of your Nexus Dashboard instance | Yes (for Nexus Dashboard) |
| NEXUS_DASHBOARD_USERNAME | Username for Nexus Dashboard | Yes (for Nexus Dashboard) |
| NEXUS_DASHBOARD_PASSWORD | Password for Nexus Dashboard | Yes (for Nexus Dashboard) |
| NEXUS_DASHBOARD_DOMAIN | Domain for Nexus Dashboard (default: local) | No |

## GPU Support

The application has been optimized for GPU usage with NVIDIA CUDA. Key features include:

- Consolidated GPU requirements in a single requirements.txt file
- NVIDIA CUDA 12.x and cuDNN 9+ library support
- GPU-accelerated PyTorch (torch==2.2.1+cu121) 
- GPU-optimized FAISS vector database (faiss-gpu)
- OpenShift deployment configured for NVIDIA GPU resource requests

The application automatically assumes GPU availability, which simplifies deployment and improves performance for GPU-intensive tasks like LLM inference and vector search operations.

## Contributors

- [@amac00](https://github.com/amac00)
- [@mpduarte](https://github.com/mpduarte)

## Contribute

Interested in improving Cisco Bridgy? We welcome contributions!
- Report issues on our GitHub repository
- Submit pull requests with improvements
- Reach out to contributors with suggestions or ideas

## License

License details to be determined. 

## External Resources

- [Intersight API Documentation](https://intersight.com/apidocs/introduction/apidocs/an/)
- [Nexus Dashboard Documentation](https://www.cisco.com/c/en/us/products/cloud-systems-management/nexus-dashboard/index.html)

---

**Note**: This is a technical demonstration project. Features and functionality may change rapidly.

