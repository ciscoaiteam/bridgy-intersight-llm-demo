#!/bin/bash
set -e

# Function to wait for MongoDB readiness
wait_for_mongodb() {
    echo "[+] Waiting for MongoDB to be ready at ${MONGODB_HOST}:${MONGODB_PORT}"
    # Keep trying to connect to MongoDB until successful
    until nc -z ${MONGODB_HOST} ${MONGODB_PORT}; do
        echo "  MongoDB is not ready yet, waiting..."
        sleep 2
    done
    echo "[+] MongoDB is ready!"
}

# Function to generate the .env file at the canonical location
generate_env_file() {
    echo "[+] Generating canonical .env file"
    
    # Define the canonical location for the .env file
    CANONICAL_ENV_FILE="/app/bridgy-main/.env"
    
    # Use /tmp for initial creation to ensure it's writable in OpenShift
    TEMP_ENV_FILE="/tmp/.env"
    
    # Copy the template file to temp
    cp /app/bridgy-main/.env.template "$TEMP_ENV_FILE"
    
    if [ $? -ne 0 ]; then
        echo "[!] Error copying template to temp file, trying to create directly"
        touch "$TEMP_ENV_FILE" || echo "[!] CRITICAL: Cannot create temp .env file!"
    fi

    # Replace the placeholder values with actual environment variables
    # Ensure MongoDB URI has no authentication
    MONGODB_URI_NO_AUTH="mongodb://${MONGODB_HOST}:${MONGODB_PORT}/${MONGODB_DB:-bridgy_db}"
    sed -i "s|{{MONGODB_URI}}|${MONGODB_URI_NO_AUTH}|g" "$TEMP_ENV_FILE"
    sed -i "s|{{CUDA_VISIBLE_DEVICES}}|${CUDA_VISIBLE_DEVICES:-0}|g" "$TEMP_ENV_FILE"
    sed -i "s|{{LLM_SERVICE_URL}}|${LLM_SERVICE_URL:-http://localhost:11434}|g" "$TEMP_ENV_FILE"
    sed -i "s|{{NEXUS_DASHBOARD_URL}}|${NEXUS_DASHBOARD_URL:-}|g" "$TEMP_ENV_FILE"
    sed -i "s|{{NEXUS_DASHBOARD_USERNAME}}|${NEXUS_DASHBOARD_USERNAME:-admin}|g" "$TEMP_ENV_FILE"
    sed -i "s|{{NEXUS_DASHBOARD_PASSWORD}}|${NEXUS_DASHBOARD_PASSWORD:-}|g" "$TEMP_ENV_FILE"
    sed -i "s|{{INTERSIGHT_API_KEY}}|${INTERSIGHT_API_KEY:-}|g" "$TEMP_ENV_FILE"
    sed -i "s|{{INTERSIGHT_PRIVATE_KEY_FILE}}|${INTERSIGHT_PRIVATE_KEY_FILE:-/app/bridgy-main/intersight.pem}|g" "$TEMP_ENV_FILE"
    sed -i "s|{{LANGSMITH_API_KEY}}|${LANGSMITH_API_KEY:-}|g" "$TEMP_ENV_FILE"
    sed -i "s|{{LANGCHAIN_PROJECT}}|${LANGCHAIN_PROJECT:-bridgy}|g" "$TEMP_ENV_FILE"

    # Copy to the canonical location
    echo "[+] Creating canonical .env file at $CANONICAL_ENV_FILE"
    cp "$TEMP_ENV_FILE" "$CANONICAL_ENV_FILE"
    
    # Create .env_example file to suppress certain warnings
    touch "/app/.env_example"
    
    # Create a symbolic link from /app/.env to the canonical location
    # This will redirect any code that looks for .env in the root
    ln -sf "$CANONICAL_ENV_FILE" "/app/.env"
    echo "[+] Created symlink from /app/.env to canonical location"

    echo "[+] Generated canonical .env file at $CANONICAL_ENV_FILE"
    # Print the .env file for debugging, but mask passwords
    cat "$CANONICAL_ENV_FILE" | grep -v PASSWORD | grep -v API_KEY
}

# Function to copy required tools to /tmp (which is writable)
copy_tools() {
    echo "[+] Copying necessary files to writable directories"
    if [ -d "/app/bridgy-main/tools" ]; then
        cp -r /app/bridgy-main/tools /tmp/
    fi
    
    # Create important directories if they don't exist
    mkdir -p /tmp/configs
    mkdir -p /tmp/embedding_cache
}

# Main initialization routine
echo "[+] Starting Bridgy AI Assistant initialization"

# 1. Copy necessary tools to writable directories
copy_tools

# 2. Generate the .env file from template
generate_env_file

# 3. Wait for MongoDB to be ready
wait_for_mongodb

# MongoDB connection will be handled by packages from requirements.txt

# 4. Set up and start Ollama
echo "[+] Setting up Ollama directory structure"
mkdir -p $OLLAMA_HOME
chmod -R 777 $OLLAMA_HOME

# Ensure Ollama can write to the models directory
mkdir -p /tmp/ollama_models
chmod -R 777 /tmp/ollama_models

# Start Ollama service
echo "[+] Starting Ollama service"
ollama serve &

# Wait for Ollama to be ready
echo "[+] Waiting for Ollama to be ready"
MAX_RETRIES=30
COUNT=0
while ! curl -s http://localhost:11434/api/version &>/dev/null && [ $COUNT -lt $MAX_RETRIES ]; do
    echo "  Waiting for Ollama service to start..."
    sleep 2
    COUNT=$((COUNT + 1))
done

if [ $COUNT -lt $MAX_RETRIES ]; then
    echo "[+] Ollama is ready!"
    
    # Download the required model
    echo "[+] Downloading gemma2 model for Ollama (this may take a while)..."
    ollama pull gemma2:latest --insecure
    
    if [ $? -eq 0 ]; then
        echo "[+] Successfully downloaded gemma2 model"
    else
        echo "[!] Warning: Failed to download gemma2 model, the expert router may not function properly"
    fi
else
    echo "[!] Warning: Ollama may not be ready, continuing anyway"
fi

# 5. Run the import verification script
echo "[+] Verifying Python imports"
python3 /app/bridgy-main/verify_imports.py

# 6. Start the Bridgy AI Assistant
echo "[+] Starting Bridgy AI Assistant"
cd /app/bridgy-main

# Set up Python paths to ensure imports work correctly
export PYTHONPATH="$PYTHONPATH:/app:/app/bridgy-main"

# No need for additional MongoDB compatibility fixes

# Run the main application
python3 main.py
