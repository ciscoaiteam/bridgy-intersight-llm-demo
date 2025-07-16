# vLLM Server Deployment on OpenShift

This directory contains the consolidated OpenShift deployment files for the vLLM server with Gemma 2 support and GPU acceleration.

## Files Overview

### Active Deployment Files
- **`vllm-complete-deployment.yaml`** - Complete deployment manifest with all resources
- **`deploy_vllm.sh`** - Automated deployment script 
- **`cleanup_old_vllm_files.sh`** - Script to archive old deployment files

### Archived Files
- **`archive/`** - Contains old/redundant deployment files for reference

## Deployment Resources

The complete deployment includes:

1. **ServiceAccount & RBAC** - Proper permissions for OpenShift SCC compliance
2. **PersistentVolumeClaims** - Optional storage for models and cache (backup to emptyDir)
3. **DeploymentConfig** - Main vLLM server deployment with GPU support
4. **Service** - ClusterIP service to expose the API
5. **Route** - External HTTPS access (optional)

## Quick Start

### Prerequisites
- OpenShift cluster with GPU nodes (NVIDIA A100 or L4)
- Logged into OpenShift CLI (`oc login`)
- Hugging Face token stored in secret `bridgy-secrets` with key `hf-token`

### Deploy vLLM Server

```bash
# Quick deployment
./deploy_vllm.sh

# Or manual deployment
oc apply -f vllm-complete-deployment.yaml
```

### Access the Server

The deployment creates:
- **Internal Service**: `http://vllm-server:8000`
- **External Route**: `https://vllm-server-<namespace>.apps.<cluster-domain>`
- **Port Forward**: `oc port-forward svc/vllm-server 8000:8000`

### API Endpoints

- **Models**: `/v1/models` - List available models
- **Chat**: `/v1/chat/completions` - OpenAI-compatible chat API
- **Completions**: `/v1/completions` - Text completion API
- **Docs**: `/docs` - Swagger API documentation

## Configuration

### Environment Variables
- `HF_TOKEN` - Hugging Face authentication token
- `TENSOR_PARALLEL_SIZE` - Number of GPUs for tensor parallelism (default: 1)
- Cache directories are automatically configured to writable `/tmp` locations

### Resource Requirements
- **CPU**: 2-4 cores
- **Memory**: 8-16 GiB
- **GPU**: 1x NVIDIA GPU (A100 80GB recommended, L4 23GB minimum)
- **Storage**: 30GiB emptyDir for model storage

### Model Configuration
- **Default Model**: `google/gemma-2-9b-it` (Gemma 2 9B Instruct)
- **Max Sequence Length**: 8192 tokens
- **Model Storage**: Downloaded at runtime to `/tmp/models`

## GPU Compatibility

### Tested Configurations
- ✅ **NVIDIA A100 80GB PCIe** - Full support with max_model_len=8192
- ⚠️ **NVIDIA L4 23GB** - Limited support, may need parameter tuning for large contexts

### GPU Memory Requirements
- **Gemma 2 9B**: ~18GB GPU memory minimum
- **KV Cache (8192 len)**: ~2.3GB additional
- **Total**: ~20GB+ GPU memory recommended

## Troubleshooting

### Common Issues

1. **Pod CrashLoopBackOff**
   ```bash
   oc logs -l app=vllm-server --tail=50
   ```

2. **GPU Memory Issues**
   - Check GPU allocation: `oc exec <pod> -- nvidia-smi`
   - Verify GPU memory: Look for "KV cache" errors in logs

3. **Model Download Issues**
   - Verify HF_TOKEN secret exists
   - Check network connectivity to Hugging Face Hub

4. **Permission Errors**
   - Ensure SecurityContext is properly configured
   - Check that cache directories use `/tmp` paths

### Useful Commands

```bash
# Check deployment status
oc get pods -l app=vllm-server
oc get svc vllm-server
oc get route vllm-server

# View logs
oc logs -l app=vllm-server -f

# Test API
curl https://vllm-server-demo1.apps.cluster/v1/models

# Port forward for local testing
oc port-forward svc/vllm-server 8000:8000
curl http://localhost:8000/v1/models
```

## Performance Optimization

### For Production
- Use PVC for persistent model storage to avoid repeated downloads
- Adjust `max_model_len` based on use case requirements
- Consider `tensor_parallel_size > 1` for multi-GPU setups
- Monitor GPU utilization and adjust `gpu_memory_utilization`

### For Development
- Use emptyDir volumes for faster startup
- Reduce model size or context length for resource-constrained environments
- Enable debug logging for troubleshooting

## Security

- Runs as non-root user (1000800000)
- Uses OpenShift SecurityContextConstraints
- HF_TOKEN stored securely in Kubernetes secret
- No sensitive data in container images
- HTTPS-only external access via OpenShift Routes

---

For issues or questions, check the main project README or logs using the troubleshooting commands above.
