# Bridgy OpenShift Deployment Integration

This document describes the consolidated deployment approach for the Bridgy ecosystem on OpenShift, including the vLLM server integration.

## Overview

The deployment has been streamlined into a single, comprehensive script that handles:
- **MongoDB** database deployment
- **vLLM Server** with Gemma 2 support and GPU acceleration  
- **Bridgy Frontend** application deployment
- **Secrets management** for configuration and API tokens

## Main Deployment Script

### `deploy_bridgy_os.sh`

The primary deployment script with flexible deployment modes:

```bash
# Full deployment (MongoDB + vLLM + Bridgy)
./deploy_bridgy_os.sh

# Deploy only vLLM components
./deploy_bridgy_os.sh --only-vllm

# Deploy only frontend components (MongoDB + Bridgy, skip vLLM)
./deploy_bridgy_os.sh --only-frontend

# Provide Hugging Face token via command line
./deploy_bridgy_os.sh --hf-token YOUR_TOKEN
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `--only-vllm` | Deploy only vLLM server components |
| `--only-frontend` | Deploy only MongoDB and Bridgy frontend |
| `--hf-token TOKEN` | Provide Hugging Face token for model download |
| `--help` | Show usage information |

## File Structure

### Active Files
```
osdeploy/
├── deploy_bridgy_os.sh                 # Main deployment script
├── vllm-complete-deployment.yaml       # Consolidated vLLM deployment
├── cleanup_old_vllm_files.sh          # Archive cleanup script
├── bridgy-optimized-deployment.yaml    # Bridgy frontend deployment
├── mongodb-*.yaml                      # MongoDB deployment files
├── bridgy-main-nodeport-service.yaml  # Bridgy service
└── README-vLLM.md                     # vLLM documentation
```

### Archived Files
```
osdeploy/archive/
├── vllm-deployment*.yaml              # Old vLLM deployments
├── vllm-service*.yaml                 # Old service definitions
├── vllm-*-persistentvolumeclaim.yaml  # Old PVC definitions
└── ...                                # Other legacy files
```

## Deployment Modes

### 1. Full Deployment (Default)
Deploys complete Bridgy ecosystem:
- MongoDB database
- vLLM server with Gemma 2 model
- Bridgy frontend application
- All necessary secrets and configurations

### 2. vLLM-Only Mode (`--only-vllm`)
Deploys only vLLM components:
- vLLM server with GPU acceleration
- Required secrets (HF token)
- Service and route for API access

### 3. Frontend-Only Mode (`--only-frontend`)
Deploys traditional Bridgy stack:
- MongoDB database  
- Bridgy frontend application
- Required secrets (Intersight credentials)

## Key Features

### Consolidated vLLM Deployment
- **Single YAML file** (`vllm-complete-deployment.yaml`) contains all vLLM resources
- **GPU acceleration** with proper node selection and resource requests
- **Security compliance** with OpenShift SecurityContextConstraints
- **Model caching** using emptyDir volumes for reliability
- **Health checks** and proper startup/readiness probes

### Intelligent Secret Management
- **Conditional secret creation** based on deployment mode
- **Multiple sources** for Hugging Face token (CLI, .env file)
- **Secure handling** of sensitive credentials
- **Automatic patching** of existing secrets when needed

### Build Integration
- **Automatic cleanup** of failed builds and pods
- **Binary builds** for both Bridgy and vLLM components
- **Progress monitoring** with timeout handling
- **Error resilience** with graceful failure handling

## Migration from Old Deployment

### What Changed
1. **Consolidated Files**: Multiple vLLM YAML files merged into single deployment
2. **Integrated Script**: vLLM deployment integrated into main script
3. **CLI Options**: Added flexible deployment modes
4. **Archive Structure**: Old files moved to `archive/` directory
5. **Enhanced Documentation**: Comprehensive README and integration guide

### Migration Steps
1. **Backup existing deployment** (if any):
   ```bash
   oc get all -l app=vllm-server -o yaml > backup-vllm.yaml
   ```

2. **Clean up old resources** (optional):
   ```bash
   oc delete all -l app=vllm-server
   ```

3. **Use new deployment script**:
   ```bash
   ./deploy_bridgy_os.sh
   ```

## Troubleshooting

### Common Issues

#### vLLM Pod Fails to Start
- **Check GPU availability**: Ensure GPU nodes are available and accessible
- **Verify HF token**: Confirm Hugging Face token is valid and has model access
- **Check logs**: `oc logs -l app=vllm-server -f`

#### Build Failures
- **Clean builds**: Script automatically cleans failed builds
- **Check source**: Verify Dockerfile and source code integrity
- **Resource limits**: Ensure sufficient resources for build pods

#### Route/Service Issues
- **Check routes**: `oc get routes`
- **Port forwarding**: Use `oc port-forward svc/vllm-server 8000:8000` as fallback
- **Service status**: `oc get svc vllm-server`

### Useful Commands

```bash
# Check all pods
oc get pods

# Monitor vLLM logs
oc logs -l app=vllm-server -f

# Check GPU allocation
oc describe nodes | grep -A 5 -B 5 "nvidia.com/gpu"

# Port forward for local access
oc port-forward svc/vllm-server 8000:8000

# Check build status
oc get builds

# Check deployment status
oc rollout status dc/vllm-server
```

## Future Enhancements

### Planned Improvements
- **Health monitoring** dashboard integration
- **Automatic scaling** based on GPU utilization
- **Model version management** for easy updates
- **Performance metrics** collection and alerting
- **Multi-model deployment** support

### Configuration Options
- **GPU memory tuning** for different GPU types
- **Model parameters** customization (max_model_len, etc.)
- **Caching strategies** optimization
- **Network policies** for enhanced security

## Support and Documentation

- **vLLM Documentation**: [README-vLLM.md](./README-vLLM.md)
- **OpenShift Resources**: Check individual YAML files for resource specifications
- **Error Logs**: Always check pod logs for detailed error information
- **Community Support**: vLLM GitHub repository and OpenShift documentation

---

**Last Updated**: July 2024  
**Version**: v2.0 (Consolidated Integration)
