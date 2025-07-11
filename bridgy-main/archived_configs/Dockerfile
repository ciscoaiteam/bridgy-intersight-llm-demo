FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOME=/app/.ollama
ENV MONGODB_URL="mongodb://localhost:27017"
ENV MONGODB_DB="bridgy_db"
ENV PYTHONPATH="/app:/app/bridgy-main:/app/bridgy:/tmp"

# Configure apt to use IPv4 only
RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4

# Set up apt to use proxy if environment variables are defined
RUN if [ ! -z "$http_proxy" ]; then echo "Acquire::http::Proxy \"$http_proxy\";" > /etc/apt/apt.conf.d/30proxy; fi && \
    if [ ! -z "$https_proxy" ]; then echo "Acquire::https::Proxy \"$https_proxy\";" >> /etc/apt/apt.conf.d/30proxy; fi

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 python3.10-venv python3.10-dev python3-pip \
    wget curl gnupg2 build-essential \
    ca-certificates software-properties-common \
    && rm -rf /var/lib/apt/lists/*
    
# Install MongoDB from official repo
RUN apt-get update && \
    apt-get install -y wget gnupg && \
    wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | apt-key add - && \
    echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && \
    apt-get install -y mongodb-org mongodb-org-server mongodb-org-shell mongodb-org-tools && \
    mkdir -p /data/db && \
    chmod -R 777 /data/db && \
    rm -rf /var/lib/apt/lists/* && \
    # Test MongoDB installation
    echo "Verifying MongoDB installation..." && \
    mongod --version

# Always install CUDA toolkit for NVIDIA GPU support
RUN apt-get update && \
    apt-get install -y gnupg ca-certificates curl && \
    mkdir -p /etc/apt/keyrings && \
    curl -4 -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub | gpg --dearmor -o /etc/apt/keyrings/nvidia.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nvidia.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64 /" > /etc/apt/sources.list.d/cuda.list && \
    apt-get update && \
    apt-get install -y cuda-toolkit-12-1 && \
    rm -rf /var/lib/apt/lists/*

# Set CUDA paths for NVIDIA GPU support
# Initialize LD_LIBRARY_PATH first to avoid Docker warning
ENV LD_LIBRARY_PATH=""
ENV PATH="/usr/local/cuda/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

# Set working directory
WORKDIR /app

# Copy project files from build context
COPY . /app/bridgy-main

# Set up Python package structure with __init__.py files (moved from runtime to build time)
RUN mkdir -p /app/bridgy-main/tools /app/bridgy-main/experts && \
    touch /app/bridgy-main/__init__.py && \
    touch /app/bridgy-main/tools/__init__.py && \
    touch /app/bridgy-main/experts/__init__.py && \
    # Create symlinks for alternate import paths
    ln -sf /app/bridgy-main /app/bridgy && \
    touch /app/bridgy/__init__.py && \
    touch /app/bridgy/tools/__init__.py && \
    touch /app/bridgy/experts/__init__.py && \
    # Create tools module in a common location
    mkdir -p /app/tools && \
    cp -r /app/bridgy-main/tools/* /app/tools/ && \
    touch /app/tools/__init__.py && \
    # Create a template .env file
    cat > /app/bridgy-main/.env.template << 'EOF'
# LLM Service Configuration (Remote)
LLM_BASE_URL=http://64.101.169.102:8000/v1
LLM_MODEL=/ai/models/Meta-Llama-3-8B-Instruct/
LLM_API_KEY=llm-api-key

# LangSmith Configuration
LANGSMITH_ENDPOINT=
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=

# Intersight API Configuration
INTERSIGHT_API_KEY=
INTERSIGHT_SECRET_KEY_PATH=

# Nexus Dashboard Configuration
NEXUS_DASHBOARD_URL=
NEXUS_DASHBOARD_USERNAME=
NEXUS_DASHBOARD_PASSWORD=
NEXUS_DASHBOARD_DOMAIN=

# MongoDB Configuration
MONGO_ENABLED=true
MONGODB_URL=mongodb://bridgy:bridgy123@mongodb:27017/bridgy_db
MONGODB_DB=bridgy_db
EOF

# Set permissions for OpenShift (allow any user to write to the necessary directories)
RUN chmod -R 777 /app && \
    mkdir -p /tmp/tools && \
    chmod -R 777 /tmp

# Install Python packages globally with fixed dependency chain
RUN cd /app/bridgy-main && \
    # First update pip and essential tools
    python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    # Install scientific stack with compatible versions
    python3 -m pip install --no-cache-dir 'numpy<2.0.0,>=1.20.0' && \
    python3 -m pip install --no-cache-dir 'scipy<1.11.0,>=1.10.0' && \
    python3 -m pip install --no-cache-dir 'scikit-learn<1.3.0,>=1.2.0' && \
    # Install MongoDB packages
    python3 -m pip install --no-cache-dir motor pymongo && \
    # Install PDF handling separately
    python3 -m pip install --no-cache-dir pypdf && \
    # Install sentence transformers after its dependencies are in place
    python3 -m pip install --no-cache-dir 'sentence-transformers<3.0.0,>=2.2.0' && \
    # Install FAISS GPU
    python3 -m pip install --no-cache-dir faiss-gpu && \
    # Then install the rest of the requirements 
    python3 -m pip install --no-cache-dir --no-dependencies -r requirements.txt || true && \
    # Create a utility script to verify Python imports
    cat > /app/verify_imports.py << 'EOF'
import sys
import importlib
import os

def verify_import(module_name):
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "__version__"):
            print(f"✅ Successfully imported {module_name} (version: {module.__version__}")
        else:
            print(f"✅ Successfully imported {module_name}")
        return True
    except ImportError as e:
        print(f"❌ Import error for {module_name}: {e}")
        return False

# Add all import paths
sys.path.extend(["/app", "/app/bridgy-main", "/app/bridgy", "/tmp"])

# Check critical modules
critical_modules = [
    "numpy", "scipy", "sklearn", "pypdf", "motor", "pymongo",
    "sentence_transformers", "faiss"
]

for module in critical_modules:
    verify_import(module)

# Try different import paths for bridgy modules
success = False

try:
    from bridgy_main.tools import pdf_loader
    print('✅ Successfully imported pdf_loader via bridgy_main')
    success = True
except ImportError as e:
    print(f'❌ Import error via bridgy_main: {e}')

try:
    from bridgy.tools import pdf_loader
    print('✅ Successfully imported pdf_loader via bridgy')
    success = True
except ImportError as e:
    print(f'❌ Import error via bridgy: {e}')

try:
    from tools import pdf_loader
    print('✅ Successfully imported pdf_loader via direct tools import')
    success = True
except ImportError as e:
    print(f'❌ Import error via direct tools: {e}')

if success:
    print("Import verification successful")
    sys.exit(0)
else:
    print("Import verification failed")
    sys.exit(1)
EOF

# Create optimized runtime initialization script
RUN cat > /app/optimized_init.sh << 'EOF'
#!/bin/bash
set -e

echo "[+] Setting up Bridgy AI Assistant - Optimized Build"

# 1. Copy any runtime-specific tools to /tmp (writable directory)
if [ ! -d "/tmp/tools" ]; then
  mkdir -p /tmp/tools
  cp -r /app/bridgy-main/tools/* /tmp/tools/
  touch /tmp/tools/__init__.py
  echo "Created /tmp/tools with __init__.py"
fi

# 2. Create .env file with environment variables from runtime
echo "[+] Creating .env file from environment variables"
cp /app/bridgy-main/.env.template /app/bridgy-main/.env
# Update with actual environment variables using sed
sed -i "s|LLM_BASE_URL=.*|LLM_BASE_URL=${LLM_BASE_URL:-http://64.101.169.102:8000/v1}|g" /app/bridgy-main/.env
sed -i "s|LLM_MODEL=.*|LLM_MODEL=${LLM_MODEL:-/ai/models/Meta-Llama-3-8B-Instruct/}|g" /app/bridgy-main/.env
sed -i "s|LLM_API_KEY=.*|LLM_API_KEY=${LLM_API_KEY:-llm-api-key}|g" /app/bridgy-main/.env
sed -i "s|LANGSMITH_ENDPOINT=.*|LANGSMITH_ENDPOINT=${LANGSMITH_ENDPOINT}|g" /app/bridgy-main/.env
sed -i "s|LANGSMITH_API_KEY=.*|LANGSMITH_API_KEY=${LANGSMITH_API_KEY}|g" /app/bridgy-main/.env
sed -i "s|LANGSMITH_PROJECT=.*|LANGSMITH_PROJECT=${LANGSMITH_PROJECT}|g" /app/bridgy-main/.env
sed -i "s|INTERSIGHT_API_KEY=.*|INTERSIGHT_API_KEY=${INTERSIGHT_API_KEY}|g" /app/bridgy-main/.env
sed -i "s|INTERSIGHT_SECRET_KEY_PATH=.*|INTERSIGHT_SECRET_KEY_PATH=${INTERSIGHT_SECRET_KEY_PATH}|g" /app/bridgy-main/.env
sed -i "s|NEXUS_DASHBOARD_URL=.*|NEXUS_DASHBOARD_URL=${NEXUS_DASHBOARD_URL}|g" /app/bridgy-main/.env
sed -i "s|NEXUS_DASHBOARD_USERNAME=.*|NEXUS_DASHBOARD_USERNAME=${NEXUS_DASHBOARD_USERNAME}|g" /app/bridgy-main/.env
sed -i "s|NEXUS_DASHBOARD_PASSWORD=.*|NEXUS_DASHBOARD_PASSWORD=${NEXUS_DASHBOARD_PASSWORD}|g" /app/bridgy-main/.env
sed -i "s|NEXUS_DASHBOARD_DOMAIN=.*|NEXUS_DASHBOARD_DOMAIN=${NEXUS_DASHBOARD_DOMAIN}|g" /app/bridgy-main/.env
sed -i "s|MONGODB_URL=.*|MONGODB_URL=${MONGODB_URL:-mongodb://bridgy:bridgy123@mongodb:27017/bridgy_db}|g" /app/bridgy-main/.env
sed -i "s|MONGODB_DB=.*|MONGODB_DB=${MONGODB_DB:-bridgy_db}|g" /app/bridgy-main/.env

# 3. Wait for MongoDB to be ready
echo "[+] Waiting for MongoDB to be ready..."
MAX_RETRIES=60
RETRY_COUNT=0

# Extract MongoDB connection details from environment variable
MONGODB_HOST=$(echo $MONGODB_URL | sed -n 's|.*mongodb://[^:]*:[^@]*@\([^:]*\).*|\1|p')
if [ -z "$MONGODB_HOST" ]; then
  MONGODB_HOST=$(echo $MONGODB_URL | sed -n 's|.*mongodb://\([^:]*\).*|\1|p')
fi
MONGODB_HOST=${MONGODB_HOST:-mongodb}

echo "Checking MongoDB connection to $MONGODB_HOST..."
while ! timeout 2 bash -c "cat < /dev/null > /dev/tcp/$MONGODB_HOST/27017" 2>/dev/null; do
  echo "Waiting for MongoDB to start... Attempt $((RETRY_COUNT+1))/$MAX_RETRIES"
  sleep 2
  RETRY_COUNT=$((RETRY_COUNT+1))
  
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "[!] Warning: MongoDB did not become ready within the timeout period. Continuing anyway..."
    break
  fi
done

# 4. Verify Python imports work
echo "[+] Verifying critical imports"
python3 /app/verify_imports.py

# 5. Start the Bridgy AI Assistant
echo "[+] Starting Bridgy AI Assistant"
cd /app/bridgy-main
exec python3 main.py --port=8443 --host=0.0.0.0
EOF

RUN chmod +x /app/optimized_init.sh

# Verify critical packages are installed and importable
RUN echo "Verifying critical packages..." && \
    python3 -c "import numpy; print('numpy version:', numpy.__version__)" && \
    python3 -c "import scipy; print('scipy version:', scipy.__version__)" && \
    python3 -c "import sklearn; print('scikit-learn version:', sklearn.__version__)" && \
    python3 -c "import pypdf; print('pypdf version:', pypdf.__version__)" && \
    python3 -c "import motor; print('motor version:', motor.version)" && \
    python3 -c "import pymongo; print('pymongo version:', pymongo.version)"

# SSL support is handled by OpenShift secrets mounted at runtime
EXPOSE 8443

# Set the entrypoint to use our optimized initialization script
ENTRYPOINT ["/app/optimized_init.sh"]
