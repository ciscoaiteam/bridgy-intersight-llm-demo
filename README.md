# Cisco Bridgy AI Assistant

![Cisco Bridgy Logo](/image.png)
 
[![Docker Build](https://img.shields.io/badge/docker-build-green?style=flat-square&logo=docker)](https://hub.docker.com/r/amac00/bridgy-ai)
[![Python Version](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)
[![CUDA Support](https://img.shields.io/badge/CUDA-12.x-green.svg)](https://developer.nvidia.com/cuda-downloads)
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
  - Retrieval-Augmented Generation (RAG) with FAISS-GPU
  - LangChain Integration
  - Streamlit-based Web Interface

## System Requirements

### Hardware
- **GPU**: Nvidia GPU with minimum 18 GB VRAM
- **CUDA**: Version 12.x
- **cuDNN**: Version 9+

### Software Prerequisites
- Python 3.10 or higher
- Internet Connectivity
- Intersight API Key & PEM file
- Nexus Dashboard credentials (for Nexus Dashboard features)
- LangSmith Key (Optional, for troubleshooting)

## Installation Methods

### Quick DCloud Installation

For the fastest setup, especially in Cisco DCloud environments, use the `docker_run.sh` script. This method provides a pre-configured, ready-to-deploy solution with minimal configuration required.

### 1. Prebuilt Container Installation (Recommended)

- Download the docker_run.sh file from the root of the repo. 
```bash
# Run the AI.sh that is deployed to get all the docker / CUDA / Python stuff installed first
./ai.sh

# Clone the Directory
git clone https://github.com/ciscoaiteam/bridgy-intersight-llm-demo.git

# Input your PAT GIT key, While the repo is public the container is still private. **Org Policy
echo ghp_### | docker login ghcr.io -u <username> --password-stdin

# Make the script executable
chmod +x docker_run.sh

# Run the installation script
./docker_run.sh
```
Notes: Update the new .env and PEM files in the config folder. These will be mounted and used by the container.

### 2. Build Your Own Container

For custom configurations or latest source code:

```bash
# Clone the repository
git clone https://github.com/ciscoaiteam/bridgy-intersight-llm-demo.git

# Run local_build_install.sh
./local_build_install.sh

# Populate the local .env file with your credentials
# (Create .env file as described in Configuration section)
```

### 3. Local Installation (Without Container)

For development or environments without Docker:

#### Prerequisites
- Python 3.10 or higher
- Nvidia GPU with 18GB+ VRAM
- CUDA 12.x
- cuDNN 9+

#### Installation Steps

```bash
# Update system packages
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev build-essential libssl-dev zlib1g-dev libjpeg-dev libtiff-dev

# Clone the repository
git clone https://github.com/ciscoaiteam/bridgy-intersight-llm-demo.git
cd bridgy-intersight-llm-demo

# Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
# Or install individual dependencies
pip install faiss-cpu langchain-community langchain python-dotenv streamlit tiktoken intersight trafilatura langchain-openai pillow pypdf

# Set up environment variables
cp .env.example .env
# Edit .env file with your specific configurations

# You will also need to update the Intersight PEM file

# Run the application
streamlit run --server.fileWatcherType none main.py --server.port 8443
```

### Post-Installation Access

After successful installation via any method, access the application at:
- `http://localhost:8443` (local access)
- `http://your_server_ip:8443` (network access)

## Configuration

Create a `.env` file with the following variables:

```
# LangSmith Configuration (Optional)
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=bridgyv2

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

1. After starting the application, you'll see the Cisco Bridgy AI Assistant interface.
2. Type your question in the chat input at the bottom of the screen.
3. The assistant will automatically route your question to the appropriate expert and display the response.
4. Questions about your Intersight environment, Nexus Dashboard, AI Pods, or general Cisco knowledge are all supported.

## Verification

Verify your installation by checking:
1. GPU compatibility
2. CUDA and cuDNN versions
3. Successful dependency installations
4. Proper API key configurations

```bash
# Verify Python and torch installation
python3 -c "import torch; print(torch.cuda.is_available())"
```

## Troubleshooting

### Common Issues
- **AI Pod Agent Errors**: 
  - Typically related to cuDNN or Torch compatibility
  - Validate installation via Python torch import
- **Nexus Dashboard Connection Issues**:
  - Verify credentials in .env file
  - Check network connectivity to Nexus Dashboard instance
  - Confirm SSL certificate settings
- **Intersight API Errors**:
  - Verify API key and PEM file
  - Check permissions for the API key
- **Port access issues**: 
  - If you can't access the application from another machine, check your firewall settings to ensure port 8443 is open
- Ensure all dependencies are correctly installed
- Check GPU drivers and CUDA configuration

## Project Structure

```
├── .streamlit/                # Streamlit configuration
├── experts/                   # Expert modules
│   ├── ai_pods_expert.py      # AI Pods expert implementation
│   ├── general_expert.py      # General Cisco knowledge expert
│   ├── intersight_expert.py   # Intersight expert implementation
│   ├── nexus_dashboard_expert.py # Nexus Dashboard expert implementation
│   └── router.py              # Expert routing logic
├── pdf/                       # Documentation PDFs
├── tools/                     # Utility tools
│   ├── intersight_api.py      # Intersight API interface
│   ├── nexus_dashboard_api.py # Nexus Dashboard API interface
│   └── pdf_loader.py          # PDF document loader
├── utils/                     # Utility functions
│   ├── avatar_manager.py      # Chat avatar management
│   └── styling.py             # UI styling utilities
├── config.py                  # Application configuration
└── main.py                    # Main application entry point
```

## Nexus Dashboard Features

The Nexus Dashboard integration provides several key capabilities:

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
