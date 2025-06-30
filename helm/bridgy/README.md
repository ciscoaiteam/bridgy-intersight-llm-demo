# Bridgy AI Assistant Helm Chart

This Helm chart deploys the complete Cisco Bridgy AI Assistant solution to a Kubernetes cluster, including:

1. **Main Bridgy Application** - The core AI assistant with Streamlit interface
2. **Bridgy API** - A FastAPI service providing API access to Ollama models

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner support in the underlying infrastructure (if persistence is enabled)
- For GPU support: NVIDIA GPU Operator installed in the cluster

## Installation

```bash
# Add the chart repository
helm repo add bridgy https://your-helm-repo-url/
helm repo update

# Install the chart
helm install bridgy bridgy/bridgy
```

## Configuration

### Important Configuration Parameters

#### Main Bridgy Application

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Image repository | `amac00/bridgy-app` |
| `image.tag` | Image tag | `latest` |
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service port | `8443` |
| `ingress.enabled` | Enable ingress | `false` |
| `persistence.enabled` | Enable persistence for Ollama models | `true` |
| `persistence.size` | PVC size | `20Gi` |
| `resources.limits.nvidia.com/gpu` | GPU resource limit | Commented out by default |

#### Bridgy API

| Parameter | Description | Default |
|-----------|-------------|---------|  
| `api.image.repository` | API image repository | `bridgy-api` |
| `api.image.tag` | API image tag | `latest` |
| `api.service.type` | API Kubernetes service type | `ClusterIP` |
| `api.service.port` | API service port | `5000` |
| `api.resources` | Resource requests and limits | See values.yaml |

### Providing Environment Variables and Secrets

You need to provide several environment variables for the application to function properly:

1. **Intersight API Credentials**:
   - Set `environment.secure.INTERSIGHT_API_KEY` with your Intersight API key ID
   - Set `intersightSecretKey` with the content of your PEM file (base64 encoded)

2. **Nexus Dashboard Credentials**:
   - Set `environment.secure.NEXUS_DASHBOARD_URL`, `NEXUS_DASHBOARD_USERNAME`, and `NEXUS_DASHBOARD_PASSWORD`

3. **LangSmith Configuration (Optional)**:
   - Set `environment.secure.LANGSMITH_API_KEY` if you're using LangSmith

4. **Remote LLM Service**:
   - Set `environment.secure.LLM_BASE_URL` and `LLM_API_KEY` for the remote LLM service

### Example: Using a values.yaml override file

Create a `myvalues.yaml` file with your configurations:

```yaml
environment:
  secure:
    INTERSIGHT_API_KEY: "your-intersight-api-key"
    NEXUS_DASHBOARD_URL: "https://your-nexus-dashboard-url"
    NEXUS_DASHBOARD_USERNAME: "admin"
    NEXUS_DASHBOARD_PASSWORD: "your-password"
    LANGSMITH_API_KEY: "your-langsmith-api-key"
    LLM_BASE_URL: "http://your-llm-service-url:8000/v1"
    LLM_API_KEY: "your-llm-api-key"

# Base64 encoded PEM file content
intersightSecretKey: "your-base64-encoded-pem-file"

# Enable GPU support if needed
resources:
  limits:
    nvidia.com/gpu: 1
```

Then install using:

```bash
helm install -f myvalues.yaml bridgy bridgy/bridgy
```

## Using GPU Support

To enable GPU support, uncomment the GPU resource limit in your values file:

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

Make sure the NVIDIA GPU Operator is installed in your Kubernetes cluster.

## Accessing the Application

If using the default ClusterIP service type:

```bash
# Port forward to access the application
kubectl port-forward svc/bridgy 8443:8443
```

Then access the application at `http://localhost:8443`

If you've enabled ingress, the application will be available at the configured ingress host.
