#!/bin/bash
# deploy_bridgy_docker.sh - Docker deployment script for Bridgy AI Assistant
# Author: Mikduart
# Date: 2025-07-11

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required dependencies
print_message "$BLUE" "Checking dependencies..."

if ! command_exists docker; then
    print_message "$RED" "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose; then
    print_message "$RED" "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Function to safely execute commands with error handling
safe_execute() {
    echo "$ $@"
    "$@" || { print_message "$RED" "Command failed with exit code $?"; exit 1; }
}

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

print_message "$GREEN" "Starting Bridgy AI Assistant Docker deployment"
print_message "$BLUE" "Current directory: $(pwd)"

# Check for .env file
ENV_FILE="../.env"
if [ -f "$ENV_FILE" ]; then
    print_message "$GREEN" "Found .env file, will use for deployment"
else
    print_message "$YELLOW" "No .env file found at $ENV_FILE, creating minimal version"
    cat > "$ENV_FILE" << EOL
# MongoDB connection
MONGODB_URI=mongodb://bridgy:bridgy123@mongodb:27017/bridgy_db

# LLM Service
LLM_SERVICE_URL=http://64.101.169.102:8000/v1
LLM_API_KEY=llm-api-key

# Nexus Dashboard
# NEXUS_DASHBOARD_URL=
# NEXUS_DASHBOARD_USERNAME=admin
# NEXUS_DASHBOARD_PASSWORD=

# Intersight API
# INTERSIGHT_API_KEY=
# INTERSIGHT_PRIVATE_KEY_FILE=

# Langsmith Configuration
LANGCHAIN_PROJECT=bridgy
EOL
    print_message "$GREEN" "Created default .env file. Please update with your credentials as needed."
fi

# Check for intersight.pem file
PEM_FILE="../config/intersight_api_key.pem"
CONFIGS_DIR="../config"
if [ ! -d "$CONFIGS_DIR" ]; then
    print_message "$YELLOW" "Creating configs directory"
    mkdir -p "$CONFIGS_DIR"
fi

if [ ! -f "$PEM_FILE" ]; then
    print_message "$YELLOW" "No Intersight PEM file found at $PEM_FILE"
    print_message "$YELLOW" "If you need Intersight integration, place your PEM file at $PEM_FILE"
fi

# Clean up any existing containers
print_message "$BLUE" "Checking for existing Bridgy containers..."
EXISTING_CONTAINERS=$(docker ps -a --filter name=bridgy -q)

if [ -n "$EXISTING_CONTAINERS" ]; then
    print_message "$YELLOW" "Found existing Bridgy containers. Cleaning up..."
    docker stop $EXISTING_CONTAINERS || true
    docker rm $EXISTING_CONTAINERS || true
    print_message "$GREEN" "Cleanup completed"
else
    print_message "$GREEN" "No existing Bridgy containers found"
fi

# Build and deploy
print_message "$BLUE" "Building and deploying Bridgy AI Assistant..."
safe_execute docker-compose build --no-cache

print_message "$GREEN" "Starting containers..."
safe_execute docker-compose up -d

# Wait for containers to be ready
print_message "$BLUE" "Waiting for containers to be ready..."
sleep 5

# Check status
print_message "$BLUE" "Checking container status..."
docker-compose ps

# Show logs
print_message "$GREEN" "Deployment completed successfully!"
print_message "$BLUE" "To view logs, run: docker-compose logs -f"
print_message "$BLUE" "To stop the application, run: docker-compose down"
print_message "$GREEN" "Bridgy AI Assistant is now running at http://localhost:8443"
