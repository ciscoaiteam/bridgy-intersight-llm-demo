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

# Function to generate the .env file
generate_env_file() {
    echo "[+] Generating .env file from template"
    # Copy the template file that was created during image build
    cp /app/bridgy-main/.env.template /app/bridgy-main/.env

    # Replace the placeholder values with actual environment variables
    sed -i "s|{{MONGODB_URI}}|${MONGODB_URI}|g" /app/bridgy-main/.env
    sed -i "s|{{CUDA_VISIBLE_DEVICES}}|${CUDA_VISIBLE_DEVICES:-0}|g" /app/bridgy-main/.env
    sed -i "s|{{LLM_SERVICE_URL}}|${LLM_SERVICE_URL:-http://localhost:11434}|g" /app/bridgy-main/.env
    sed -i "s|{{NEXUS_DASHBOARD_URL}}|${NEXUS_DASHBOARD_URL:-}|g" /app/bridgy-main/.env
    sed -i "s|{{NEXUS_DASHBOARD_USERNAME}}|${NEXUS_DASHBOARD_USERNAME:-admin}|g" /app/bridgy-main/.env
    sed -i "s|{{NEXUS_DASHBOARD_PASSWORD}}|${NEXUS_DASHBOARD_PASSWORD:-}|g" /app/bridgy-main/.env
    sed -i "s|{{INTERSIGHT_API_KEY}}|${INTERSIGHT_API_KEY:-}|g" /app/bridgy-main/.env
    sed -i "s|{{INTERSIGHT_PRIVATE_KEY_FILE}}|${INTERSIGHT_PRIVATE_KEY_FILE:-/app/bridgy-main/configs/intersight_api_key.pem}|g" /app/bridgy-main/.env
    sed -i "s|{{LANGSMITH_API_KEY}}|${LANGSMITH_API_KEY:-}|g" /app/bridgy-main/.env
    sed -i "s|{{LANGCHAIN_PROJECT}}|${LANGCHAIN_PROJECT:-bridgy}|g" /app/bridgy-main/.env

    echo "[+] Generated .env file:"
    # Print the .env file for debugging, but mask passwords
    cat /app/bridgy-main/.env | grep -v PASSWORD | grep -v API_KEY
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

# 4. Run the import verification script
echo "[+] Verifying Python imports"
python3 /app/bridgy-main/verify_imports.py

# 5. Start the Bridgy AI Assistant
echo "[+] Starting Bridgy AI Assistant"
cd /app/bridgy-main
python3 -m assistant.app
