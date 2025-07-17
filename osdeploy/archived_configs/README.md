# Bridgy AI Assistant Deployment Guide

This directory contains files and configurations needed to deploy the Bridgy AI Assistant to OpenShift. The project now also supports Docker Compose deployment for local development and testing.

## OpenShift Deployment

### Recent Improvements

The OpenShift deployment process has been significantly improved with the following enhancements:

1. **Robust Cleanup**: The `deploy_bridgy_os.sh` script now properly cleans up old bridgy-main deployments, including:
   - Failed build pods and builds
   - Orphaned replication controllers
   - Pods stuck in CrashLoopBackOff state
   - Deployment pods with careful filtering to target only bridgy-main resources

2. **Permission Fixes**: Updated Dockerfile and initialization scripts to comply with OpenShift's arbitrary user IDs:
   - Added `chmod -R 777 /app` to the Dockerfile
   - Now generates the `.env` file in `/tmp` (writable) and symlinks to expected location
   - Proper error handling when generating configuration files

3. **Application Startup**: Corrected the application launch mechanism:
   - Setting `PYTHONPATH` properly in the deployment config
   - Using `python3 main.py` instead of the non-existent module
   - Added missing dependencies like `motor` and `fastapi`

4. **Environment and Secret Handling**: Improved management of environment variables:
   - Secure handling of MongoDB connection string
   - LLM service configuration with Meta-Llama-3-8B-Instruct model
   - SSL certificates and secrets via OpenShift secrets

### Environment Variables Configuration

The application requires environment variables for external services. These are managed through secrets and ConfigMaps.

1. **Required Environment Variables**:

   ```yaml
   # LLM Service Configuration - Remote Meta-Llama-3 model
   LLM_SERVICE_URL: "http://64.101.169.102:8000/v1"
   LLM_MODEL: "/ai/models/Meta-Llama-3-8B-Instruct/"
   LLM_API_KEY: "llm-api-key"
   
   # MongoDB Configuration
   MONGODB_URI: "mongodb://<username>:<password>@mongodb:27017/bridgy_db"
   
   # Nexus Dashboard Configuration (optional)
   NEXUS_DASHBOARD_URL: "https://your.nexus.dashboard.url/"
   
   # Intersight Configuration (optional)
   INTERSIGHT_API_KEY: "your_intersight_api_key"
   INTERSIGHT_PRIVATE_KEY_FILE: "/app/bridgy-main/configs/intersight_api_key.pem"
   
   # Langsmith Configuration (optional)
   LANGCHAIN_PROJECT: "bridgy"
   ```

2. **Setting Up Secrets**:
   
   Sensitive credentials are managed via OpenShift secrets:
   ```bash
   oc create secret generic bridgy-secrets \
      --from-literal=nexus-dashboard-username=<your_username> \
      --from-literal=nexus-dashboard-password=<your_password> \
      --from-literal=nexus-dashboard-url=https://your.nexus.dashboard.url/ \
      --from-literal=intersight-api-key=<your_intersight_api_key> \
      --from-literal=langsmith-api-key=<your_langsmith_api_key>
   ```

### Deployment Process

1. **Deploy Using the Script**:
   ```bash
   ./deploy_bridgy_os.sh
   ```
   This script handles:
   - Cleanup of old resources
   - Building and pushing the container image
   - Creating necessary configs and secrets
   - Deploying MongoDB and the Bridgy application
   - Setting up routes and services

2. **Verify Deployment**:
   ```bash
   oc get pods | grep bridgy-main
   oc logs bridgy-main-<pod-id>
   ```

## Docker Deployment (New!)

For development and testing, you can now use Docker Compose:

1. **Setup**:
   The Docker configuration is in the `dockerdeploy` directory with:
   - `docker-compose.yml` - Services configuration matching OpenShift
   - `deploy_bridgy_docker.sh` - Easy deployment script

2. **Deployment**:
   ```bash
   cd ../dockerdeploy
   ./deploy_bridgy_docker.sh
   ```

3. **Docker Environment**:
   The Docker setup mirrors the OpenShift configuration, using the same:
   - Remote LLM service (Meta-Llama-3-8B-Instruct)
   - MongoDB database structure
   - Integration points for Nexus Dashboard and Intersight
   - Environment variables and secrets management

## Accessing the Application

1. **OpenShift Access**:
   - **Route**: `https://bridgy-main-<namespace>.apps.<cluster-domain>`
   - **NodePort**: `http://<node-ip>:30843`

2. **Docker Access**:
   - `http://localhost:8443`

## Troubleshooting

1. **Pod Startup Issues**:
   - Check logs: `oc logs bridgy-main-<pod-id>`
   - Verify MongoDB connection: `oc get pods | grep mongodb`
   - Ensure secrets are properly mounted

2. **Resource Cleanup**:
   - If deployment fails, run cleanup: `./deploy_bridgy_os.sh cleanup`
   - For Docker: `cd ../dockerdeploy && docker-compose down`
