FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOME=/app/.ollama
ENV MONGODB_URL="mongodb://localhost:27017"
ENV MONGODB_DB="bridgy_db"

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

# Install Ollama with IPv4 only
RUN curl -4 -fsSL https://ollama.com/install.sh | sh

# Add Ollama to the PATH
ENV PATH="/root/.ollama/bin:${PATH}"

# Set CUDA paths for NVIDIA GPU support
# Initialize LD_LIBRARY_PATH first to avoid Docker warning
ENV LD_LIBRARY_PATH=""
ENV PATH="/usr/local/cuda/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

# Configure Ollama model storage
RUN mkdir -p /config/ollama
ENV OLLAMA_MODELS=/config/ollama

# Set working directory
WORKDIR /app

# Copy project files from build context
COPY . /app/bridgy-main

# Set permissions for OpenShift (allow any user to write to the necessary directories)
RUN mkdir -p $OLLAMA_HOME && \
    chmod -R 777 /app && \
    chmod -R 777 $OLLAMA_HOME

# Create a simple entrypoint script for the container
RUN echo '#!/bin/bash' > /app/entrypoint.sh && \
    echo 'echo "[+] Creating Ollama directory structure"' >> /app/entrypoint.sh && \
    echo 'mkdir -p $OLLAMA_HOME' >> /app/entrypoint.sh && \
    echo 'chmod -R 777 /app' >> /app/entrypoint.sh && \
    echo 'chmod -R 777 $OLLAMA_HOME' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo '# Start MongoDB service with proper configuration' >> /app/entrypoint.sh && \
    echo 'echo "[+] Starting MongoDB service..."' >> /app/entrypoint.sh && \
    echo 'mkdir -p /data/db' >> /app/entrypoint.sh && \
    echo 'chmod -R 777 /data/db' >> /app/entrypoint.sh && \
    echo 'nohup mongod --bind_ip_all --port 27017 &' >> /app/entrypoint.sh && \
    echo 'MONGO_PID=$!' >> /app/entrypoint.sh && \
    echo 'echo "MongoDB started with PID $MONGO_PID, waiting for it to be ready..."' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo '# Wait for MongoDB to be ready' >> /app/entrypoint.sh && \
    echo 'MAX_TRIES=30' >> /app/entrypoint.sh && \
    echo 'TRIES=0' >> /app/entrypoint.sh && \
    echo 'echo "Waiting for MongoDB to accept connections..."' >> /app/entrypoint.sh && \
    echo 'while [ $TRIES -lt $MAX_TRIES ]; do' >> /app/entrypoint.sh && \
    echo '  if mongo --eval "db.version()" &> /dev/null; then' >> /app/entrypoint.sh && \
    echo '    echo "MongoDB is ready!"' >> /app/entrypoint.sh && \
    echo '    break' >> /app/entrypoint.sh && \
    echo '  fi' >> /app/entrypoint.sh && \
    echo '  echo "Attempt $((TRIES+1))/$MAX_TRIES: MongoDB not ready yet, waiting..."' >> /app/entrypoint.sh && \
    echo '  sleep 2' >> /app/entrypoint.sh && \
    echo '  TRIES=$((TRIES+1))' >> /app/entrypoint.sh && \
    echo 'done' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo 'if [ $TRIES -eq $MAX_TRIES ]; then' >> /app/entrypoint.sh && \
    echo '  echo "ERROR: MongoDB failed to start after $MAX_TRIES attempts"' >> /app/entrypoint.sh && \
    echo '  ps aux | grep mongo' >> /app/entrypoint.sh && \
    echo '  ls -la /data/db' >> /app/entrypoint.sh && \
    echo 'else' >> /app/entrypoint.sh && \
    echo '  echo "MongoDB is running and accepting connections"' >> /app/entrypoint.sh && \
    echo 'fi' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo '# Start Ollama server' >> /app/entrypoint.sh && \
    echo 'echo "[+] Starting Ollama..."' >> /app/entrypoint.sh && \
    echo 'ollama serve &' >> /app/entrypoint.sh && \
    echo 'sleep 5' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo '# Set PYTHONPATH' >> /app/entrypoint.sh && \
    echo 'export PYTHONPATH="$PYTHONPATH:/app/bridgy-main"' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo '# Start the application' >> /app/entrypoint.sh && \
    echo 'echo "[+] Starting Bridgy application..."' >> /app/entrypoint.sh && \
    echo 'cd /app/bridgy-main' >> /app/entrypoint.sh && \
    echo 'python3 main.py --port=8443 --host=0.0.0.0' >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Install Python packages globally with fixed dependency chain
RUN mkdir -p /app/bridgy-main && \
    cd /app/bridgy-main && \
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
    # Verify critical packages are installed and importable
    echo "Verifying critical packages..." && \
    python3 -c "import numpy; print('numpy version:', numpy.__version__)" && \
    python3 -c "import scipy; print('scipy version:', scipy.__version__)" && \
    python3 -c "import sklearn; print('scikit-learn version:', sklearn.__version__)" && \
    python3 -c "import pypdf; print('pypdf version:', pypdf.__version__)" && \
    python3 -c "import motor; print('motor version:', motor.version)" && \
    python3 -c "import pymongo; print('pymongo version:', pymongo.version)"

# SSL support is handled by OpenShift secrets mounted at runtime
EXPOSE 8443
