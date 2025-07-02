FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
# Set Ollama home directory to a location that will be writable in OpenShift
ENV OLLAMA_HOME=/app/.ollama

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

# Create entrypoint script - using multiple RUN commands to avoid syntax issues
RUN echo '#!/bin/bash' > /app/entrypoint.sh
RUN echo '# This file is generated during build' >> /app/entrypoint.sh
RUN echo 'echo "[+] Creating Ollama directory structure"' >> /app/entrypoint.sh
RUN echo 'mkdir -p $OLLAMA_HOME' >> /app/entrypoint.sh
RUN echo 'echo "[+] Starting Ollama..."' >> /app/entrypoint.sh
RUN echo 'ollama serve &' >> /app/entrypoint.sh
RUN echo '' >> /app/entrypoint.sh
RUN echo 'sleep 5' >> /app/entrypoint.sh
RUN echo '' >> /app/entrypoint.sh
RUN echo 'echo "[+] Starting Bridgy..."' >> /app/entrypoint.sh
RUN echo 'cd /app/bridgy-main' >> /app/entrypoint.sh
RUN echo 'source /app/bridgy-main/venv/bin/activate' >> /app/entrypoint.sh
RUN echo 'streamlit run main.py --server.port=8443 --server.address=0.0.0.0' >> /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Create a comprehensive requirements file inline (excluding torch which we'll install separately)
RUN echo 'aiohappyeyeballs==2.6.1\naiohttp==3.11.14\naiosignal==1.3.2\naltair==5.5.0\nannotated-types==0.7.0\nanyio==4.9.0\nasync-timeout==4.0.3\nattrs==25.3.0\nblinker==1.9.0\ncachetools==5.5.2\ncertifi==2025.1.31\ncharset-normalizer==3.4.1\nclick==8.1.8\ndataclasses-json==0.6.7\ndistro==1.9.0\ndnspython==2.7.0\nexceptiongroup==1.2.2\nfaiss-gpu==1.7.2\nfilelock==3.18.0\nFlask==3.1.0\nfrozenlist==1.5.0\nfsspec==2025.3.0\ngitdb==4.0.12\nGitPython==3.1.44\ngnupg==2.3.1\ngreenlet==3.1.1\nh11==0.14.0\nhttpcore==1.0.7\nhttpx==0.28.1\nhttpx-sse==0.4.0\nhuggingface-hub==0.29.3\nidna==3.10\nimportlib_metadata==8.6.1\nintersight==1.0.11.2025021903\nitsdangerous==2.2.0\nJinja2==3.1.6\njiter==0.9.0\njoblib==1.4.2\njsonpatch==1.33\njsonpointer==3.0.0\njsonschema==4.23.0\njsonschema-specifications==2024.10.1\nlangchain==0.3.21\nlangchain-community==0.3.20\nlangchain-core==0.3.48\nlangchain-ollama==0.3.0\nlangchain-openai==0.3.10\nlangchain-text-splitters==0.3.7\nlangsmith==0.3.18\nMarkupSafe==3.0.2\nmarshmallow==3.26.1\nmpmath==1.3.0\nmultidict==6.2.0\nmypy-extensions==1.0.0\nnarwhals==1.32.0\nnetworkx==3.2.1\nnumpy==1.26.4\nollama==0.4.7\nopenai==1.68.2\norjson==3.10.16\npackaging==24.2\npandas==2.2.3\npem==23.1.0\npillow==11.1.0\npropcache==0.3.0\nprotobuf==5.29.4\npyarrow==19.0.1\npycryptodome==3.22.0\npydantic==2.10.6\npydantic-settings==2.8.1\npydantic_core==2.27.2\npydeck==0.9.1\npymongo==4.11.1\npypdf==5.4.0\npython-dateutil==2.9.0.post0\npython-dotenv==1.0.1\npytz==2025.1\nPyYAML==6.0.2\nreferencing==0.36.2\nregex==2024.11.6\nrequests==2.32.3\nrequests-toolbelt==1.0.0\nrpds-py==0.23.1\nsafetensors==0.5.3\nscikit-learn==1.6.1\nscipy==1.13.1\nsentence-transformers>=2.6.0\nsix==1.15.0\nsmmap==5.0.2\nsniffio==1.3.1\nSQLAlchemy==2.0.39\nstreamlit==1.43.2\nsympy==1.13.1\ntenacity==9.0.0\nthreadpoolctl==3.6.0\ntiktoken==0.9.0\ntokenizers==0.21.1\ntoml==0.10.2\ntornado==6.4.2\ntqdm==4.67.1\ntransformers>=4.38.0\ntyping-inspect==0.9.0\ntyping_extensions==4.12.2\ntzdata==2025.2\nurllib3==2.3.0\nwatchdog==6.0.0\nWerkzeug==3.1.3\nyarl==1.18.3\nzipp==3.21.0\nzstandard==0.23.0' > /app/requirements.txt && \
    grep -v torch /app/requirements.txt > /app/basic_requirements.txt

# Set up Python environment
RUN python3.10 -m venv /app/bridgy-main/venv && \
    chmod -R +x /app/bridgy-main/venv/bin && \
    /app/bridgy-main/venv/bin/python -m pip install --upgrade pip && \
    echo "Installing basic packages first..." && \
    /app/bridgy-main/venv/bin/python -m pip install -r /app/basic_requirements.txt && \
    echo "Installing PyTorch with CUDA..." && \
    /app/bridgy-main/venv/bin/python -m pip install torch==2.2.1 --index-url https://download.pytorch.org/whl/cu121

EXPOSE 8443
