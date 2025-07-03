# OpenShift Deployment Guide

This directory contains files needed to deploy the Bridgy AI Assistant to OpenShift.

## Environment Variables Configuration

The application requires several environment variables to function properly. These include credentials for external services like Intersight, Nexus Dashboard, and LangSmith, as well as configuration for the remote LLM service.

### Setting Up Environment Variables

1. Copy the template ConfigMap to create your actual ConfigMap:
   ```bash
   cp bridgy-main-env-configmap.template.yaml bridgy-main-env-configmap.yaml
   ```

2. Edit `bridgy-main-env-configmap.yaml` with your actual credentials and configuration values:
   ```yaml
   # Remote LLM Service Configuration
   LLM_BASE_URL: "http://64.101.169.102:8000/v1"  # URL to the remote LLM service
   LLM_MODEL: "/ai/models/Meta-Llama-3-8B-Instruct/"  # Path to the model on the remote service
   LLM_API_KEY: "your_actual_llm_api_key"  # API key for authentication
   
   # Intersight Configuration
   INTERSIGHT_API_KEY: "your_actual_intersight_api_key"
   INTERSIGHT_SECRET_KEY_PATH: "/path/to/your/intersight.pem"
   
   # Nexus Dashboard Configuration
   NEXUS_DASHBOARD_URL: "https://your.nexus.dashboard.url/"
   NEXUS_DASHBOARD_USERNAME: "your_actual_username"
   NEXUS_DASHBOARD_PASSWORD: "your_actual_password"
   NEXUS_DASHBOARD_DOMAIN: "your_actual_domain"
   ```

3. Apply the ConfigMap to your OpenShift cluster:
   ```bash
   oc apply -f bridgy-main-env-configmap.yaml
   ```

**Note**: The `bridgy-main-env-configmap.yaml` file is added to `.gitignore` to prevent accidentally committing sensitive credentials to the repository. Only the template version should be committed.

## Deployment

Run the following commands to deploy the application:

1. Deploy the application:
   ```bash
   ./deploy_bridgy_openshift.sh
   ```

2. Verify the pod is running:
   ```bash
   oc get pods | grep bridgy-main
   ```

## Accessing the Application

The application is exposed through:

1. **NodePort Service** on port 30843:
   - Access via: `http://<node-ip>:30843`
   - Where `<node-ip>` is any OpenShift node IP address

2. **OpenShift Route**:
   - Access via: `https://bridgy-main-<namespace>.apps.<cluster-domain>`
   - This provides edge TLS termination with automatic HTTP to HTTPS redirection
