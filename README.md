# Cisco Bridgy AI Assistant

![Cisco Intersight Logo](https://storage.googleapis.com/blogs-images-new/ciscoblogs/1/2021/09/Intersight-Icon.png)
[![Docker Build](https://img.shields.io/badge/docker-build-green?style=flat-square&logo=docker)](https://hub.docker.com/r/amac00/bridgy-ai)
[![Python Version](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-TBD-yellow.svg)](#license)



## Overview

Cisco Bridgy is an advanced AI assistant designed to provide specialized expertise in Cisco infrastructure, focusing on Intersight, Nexus Dashboard, AI Pods, and general Cisco knowledge. Utilizing a sophisticated "Mix of Experts" model, the assistant routes queries to specialized knowledge domains for precise and context-aware responses.

## Key Features

- **Multi-Expert Routing**:
  - Intersight Expert: Server inventory and infrastructure management
  - Nexus Dashboard Expert: Fabric management and network configuration
  - AI Pods Expert: AI infrastructure and LLM hardware insights
  - General Cisco Knowledge Expert

- **Advanced Technology Stack**:
  - Retrieval-Augmented Generation (RAG) with FAISS-CPU
  - Remote LLM Integration with Meta-Llama-3-8B-Instruct
  - LangChain Integration
  - Streamlit-based Web Interface

## System Requirements

### Software Prerequisites
- Python 3.10
- Internet Connectivity
- Intersight API Key & PEM
- Nexus Dashboard credentials (for Nexus Dashboard functionality)
- LangSmith Key (Optional, for troubleshooting)

## Installation Methods

### Quick DCloud Installation

For the fastest setup, especially in Cisco DCloud environments, use the `docker_run.sh` script. This method provides a pre-configured, ready-to-deploy solution with minimal configuration required.

### 1. Prebuilt Container Installation (Recommended)

- Download the docker_run.sh file from the root of the repo. 
```
#Run the AI.sh that is deployed to get all the docker / CUDA / Python stuff installed first
./ai.sh

# Clone the Directory ( You could do just the docker_run.sh file but maybe you want to see what else is in this ) 
git clone https://github.com/ciscoaiteam/bridgy-intersight-llm-demo.git

# Input your PAT GIT key, While the repo is public the container is still private. **Org Policy
echo ghp_### | docker login ghcr.io -u <username> --password-stdin

# Make the script executable
chmod +x docker_run.sh

# Run the installation script
./docker_run.sh
```
Notes:  Update the new .env and PEM files in the config folder. These will be mounted and used by the container. 


### 2. Build Your Own Container

For custom configurations or latest source code:

```bash
# Clone the repository
git clone https://github.com/ciscoaiteam/bridgy-intersight-llm-demo.git

#Run local_build_install.sh
./local_build_install.sh

# Populate the local .env file with your credentials
# (Create .env file as described in Configuration section)
```

### 3. Local Installation (Without Container)

For development or environments without Docker:

#### Prerequisites
- Python 3.10

#### Installation Steps

```bash
# Update system packages
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev build-essential libssl-dev zlib1g-dev libjpeg-dev libtiff-dev

# Clone the repository
git clone https://github.com/ciscoaiteam/bridgy-intersight-llm-demo.git
cd bridgy

# Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install system dependencies
sudo apt-get install -y python3-pip python3-dev build-essential libssl-dev zlib1g-dev libjpeg-dev libtiff-dev

# Install Python dependencies
pip install -r requirements.txt

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
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=bridgyv2
INTERSIGHT_API_KEY=your_intersight_api_key_id
NEXUS_DASHBOARD_URL=your_nexus_dashboard_url
NEXUS_DASHBOARD_USERNAME=your_nexus_dashboard_username
NEXUS_DASHBOARD_PASSWORD=your_nexus_dashboard_password
```

## Verification

Verify your installation by checking:
1. Successful dependency installations
2. Proper API key configurations

```bash
# Verify Python installation
python3 -c "import langchain; print('LangChain installed successfully')"
```

## Troubleshooting

### Common Issues
- **API Connection Errors**: 
  - Check your API keys and credentials in the .env file
  - Ensure network connectivity to the remote LLM service
- **Nexus Dashboard Connection Issues**:
  - Verify the URL format (should include https://)
  - Check username/password credentials
  - SSL verification may need to be disabled for self-signed certificates
- Ensure all dependencies are correctly installed

## Project Structure

```
├── .streamlit/                # Streamlit configuration
├── bridgyv2-main/            
│   ├── experts/               # Expert modules
│   │   ├── router.py          # Query routing logic
│   │   ├── intersight_expert.py
│   │   ├── ai_pods_expert.py
│   │   └── general_expert.py
│   ├── tools/                 # Utility tools
│   │   ├── intersight_api.py  # Intersight API integration
│   │   └── pdf_loader.py      # PDF document loading
│   ├── utils/                 # Utility functions
│   └── main.py                # Main application entry point
├── config/                    # Configuration files
└── docker_run.sh              # Docker deployment script
```

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
