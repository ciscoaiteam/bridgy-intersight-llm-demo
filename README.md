# Cisco Bridgy AI Assistant

![Cisco Intersight Logo](https://storage.googleapis.com/blogs-images-new/ciscoblogs/1/2021/09/Intersight-Icon.png)
[![Docker Build](https://img.shields.io/badge/docker-build-green?style=flat-square&logo=docker)](https://hub.docker.com/r/amac00/bridgy-ai)
[![Python Version](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)
[![CUDA Support](https://img.shields.io/badge/CUDA-12.x-green.svg)](https://developer.nvidia.com/cuda-downloads)
[![License](https://img.shields.io/badge/License-TBD-yellow.svg)](#license)



## 🚀 Overview

Cisco Bridgy is an advanced AI assistant designed to provide specialized expertise in Cisco infrastructure, focusing on Intersight, AI Pods, and general Cisco knowledge. Utilizing a sophisticated "Mix of Experts" model, the assistant routes queries to specialized knowledge domains for precise and context-aware responses.

## ✨ Key Features

- **Multi-Expert Routing**:
  - Intersight Expert: Server inventory and infrastructure management
  - AI Pods Expert: AI infrastructure and LLM hardware insights
  - General Cisco Knowledge Expert

- **Advanced Technology Stack**:
  - Retrieval-Augmented Generation (RAG) with FAISS-GPU
  - Embedding Model: [Specific Embedding Model Name]
  - Inferencing via Ollama with Gemma2 (9B model)
  - LangChain Integration
  - Streamlit-based Web Interface

## 🖥️ System Requirements

### Hardware
- **GPU**: Nvidia GPU with minimum 18 GB VRAM
- **CUDA**: Version 12.x
- **cuDNN**: Version 9+

### Software Prerequisites
- Python 3.10
- Internet Connectivity
- Intersight API Key
- LangSmith Key (Optional, for troubleshooting)

## 🛠️ Installation Methods

### Quick DCloud Installation

For the fastest setup, especially in Cisco DCloud environments, use the `install.sh` script. This method provides a pre-configured, ready-to-deploy solution with minimal configuration required.

### 1. Prebuilt Container Installation (Recommended)

Before installation, generate a GitHub **Personal Access Token (PAT)** with the following scopes:

- `repo` – for private repository access  
- `read:packages` – for downloading Docker containers from GitHub Container Registry

#### ✅ Generate Your PAT:
1. Visit: [GitHub PAT Settings](https://github.com/settings/tokens?type=classic)
2. Click **"Generate new token (classic)"**
3. Select the following scopes:
   - `repo`
   - `read:packages`
4. Click **Generate token** and copy the token somewhere safe.

> ⚠️ Treat this token like a password. Keep it secure.

---

#### 🐳 Docker Authentication (one-time setup)

```bash
echo YOUR_GITHUB_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

---

#### 📦 Download and Install

```bash
# Export your GitHub PAT (replace with your actual token or use a secure method to load it)
export GH_PAT=your_token_here

# Download the install script with authentication
wget --header="Authorization: token $GH_PAT" https://raw.githubusercontent.com/AMac00/bridgy/main/install.sh

# Make the script executable
chmod +x install.sh

# Run the installation script
./install.sh
```




### 2. Build Your Own Container

For custom configurations or latest source code:

```bash
# Clone the repository
git clone https://github.com/AMac00/bridgy.git
cd bridgy

# Populate the local .env file with your credentials
# (Create .env file as described in Configuration section)

# Build the Docker container
docker build --no-cache -t bridgyv2-app .

# Run the container
docker run --rm -it --gpus all -p 8443:8443 bridgyv2-app
```

### 3. Local Installation (Without Container)

For development or environments without Docker:

#### Prerequisites
- Python 3.10
- Nvidia GPU with 18GB+ VRAM
- CUDA 12.x
- cuDNN 9+

#### Installation Steps

```bash
# Update system packages
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev build-essential libssl-dev zlib1g-dev libjpeg-dev libtiff-dev

# Clone the repository
git clone https://github.com/AMac00/bridgy.git
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

# Run the application
streamlit run --server.fileWatcherType none main.py --server.port 8443
```

### Post-Installation Access

After successful installation via any method, access the application at:
- `http://localhost:8443` (local access)
- `http://your_server_ip:8443` (network access)

## 📋 Configuration

Create a `.env` file with the following variables:

```
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=bridgyv2
INTERSIGHT_API_KEY=your_intersight_api_key_id
```

## 🔍 Verification

Verify your installation by checking:
1. GPU compatibility
2. CUDA and cuDNN versions
3. Successful dependency installations
4. Proper API key configurations

```bash
# Verify Python and torch installation
python3 -c "import torch; print(torch.cuda.is_available())"
```

## 🛡️ Troubleshooting

### Common Issues
- **AI Pod Agent Errors**: 
  - Typically related to cuDNN or Torch compatibility
  - Validate installation via Python torch import
- Ensure all dependencies are correctly installed
- Check GPU drivers and CUDA configuration

## 📂 Project Structure

```
├── .streamlit/                # Streamlit configuration
├── experts/                   # Expert modules
├── pdf/                       # Documentation PDFs
├── tools/                     # Utility tools
├── utils/                     # Utility functions
├── config.py                  # Application configuration
└── main.py                    # Main application entry point
```

## 👥 Contributors

- [@amac00](https://github.com/amac00)
- [@noahsdonaldson](https://github.com/noahsdonaldson)

## 💡 Contribute

Interested in improving Cisco Bridgy? We welcome contributions!
- Report issues on our GitHub repository
- Submit pull requests with improvements
- Reach out to contributors with suggestions or ideas

## 📄 License

License details to be determined. 

## 🔗 External Resources

- [Intersight API Documentation](https://intersight.com/apidocs/introduction/apidocs/an/)

---

**Note**: This is a technical demonstration project. Features and functionality may change rapidly.
