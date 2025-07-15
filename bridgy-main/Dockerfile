FROM python:3.9

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    unzip \
    libsndfile1 \
    libasound2-dev \
    cmake \
    sudo \
    gnupg \
    netcat-openbsd \
    wget

# Using remote vLLM server instead of local LLM processing

# Install Python dependencies
WORKDIR /app

# Copy requirements
COPY ./bridgy-main/requirements.txt /app/requirements.txt

# Install Python packages
RUN pip install --no-cache-dir -r /app/requirements.txt

# Use versions from requirements.txt only

# Copy application code
COPY ./bridgy-main /app/bridgy-main

# Copy our external script files
COPY ./bridgy-main/verify_imports.py /app/bridgy-main/
COPY ./bridgy-main/optimized_init.sh /app/bridgy-main/
COPY ./bridgy-main/.env.template /app/bridgy-main/

# SSL certificates are already in the bridgy-main directory and will be copied with the app code

# Set permissions for OpenShift (needs to be writable by any user)
RUN chmod -R 777 /app

# Create Python module structure at build time
RUN touch /app/bridgy-main/__init__.py && \
    mkdir -p /app/bridgy-main/tools && \
    touch /app/bridgy-main/tools/__init__.py && \
    mkdir -p /app/bridgy-main/experts && \
    touch /app/bridgy-main/experts/__init__.py && \
    ln -sf /app/bridgy-main /app/bridgy && \
    mkdir -p /app/bridgy-main/embedding_cache && \
    mkdir -p /tmp/embedding_cache && \
    mkdir -p /tmp/configs && \
    chmod -R 777 /tmp && \
    chmod -R 777 /app/bridgy-main/embedding_cache

# Make scripts executable
RUN chmod +x /app/bridgy-main/verify_imports.py && chmod +x /app/bridgy-main/optimized_init.sh

# Set environment variables
ENV PYTHONPATH=/app:/app/bridgy-main:/app/bridgy:/tmp
ENV PYTHONUNBUFFERED=1
ENV MONGODB_HOST=mongodb
ENV MONGODB_PORT=27017
ENV MONGODB_URI=mongodb://mongodb:27017/bridgy_db
ENV MONGODB_URL=mongodb://mongodb:27017/bridgy_db
ENV MONGO_ENABLED=true
ENV HOME=/tmp
# Using remote vLLM server with OpenAI-compatible API instead of local Ollama
ENV LLM_SERVICE_URL=http://vllm-server:8000/v1
ENV LLM_MODEL=gemma-2-9b
ENV LLM_API_KEY=llm-api-key

# Set the initialization script as the entrypoint
ENTRYPOINT ["/app/bridgy-main/optimized_init.sh"]
