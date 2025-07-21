# vLLM Server for Gemma 2

This directory contains a Docker setup for running Gemma 2 with vLLM, providing an OpenAI-compatible API endpoint for the Bridgy application.

## Overview

The setup includes:
- A multi-stage Dockerfile that builds and runs vLLM with Gemma 2 model
- A docker-compose.yml file for easy deployment
- Support for NVIDIA GPUs for accelerated inference

## Requirements

- Docker and Docker Compose
- NVIDIA GPU with CUDA support
- NVIDIA Container Toolkit installed
- Hugging Face account with access to Gemma 2 (google/gemma-2-9b-it)

## Getting Started

1. Set up your Hugging Face token (required for downloading the Gemma 2 model):
   ```bash
   export HF_TOKEN=your_hugging_face_token
   ```

2. Build and run the container:
   ```bash
   cd dockerdeploy
   docker-compose up -d
   ```
   
   Note: The vLLM service has been integrated into the main docker-compose.yml file in the dockerdeploy directory.

3. The server will be available at `http://localhost:8000` with OpenAI-compatible API endpoints.

## Integration with Bridgy

To use this vLLM server with Bridgy, update the following environment variables in your Bridgy configuration:

```
LLM_SERVICE_URL=http://localhost:8000/v1
LLM_MODEL=gemma-2-9b
LLM_API_KEY=not-needed
```

## Model Storage

Models are stored in `./models` directory and will persist between container restarts.

## Advanced Configuration

- **TENSOR_PARALLEL_SIZE**: Set this to the number of GPUs you want to use (default: 1)
- **Model Parameters**: Adjust parameters in `run_vllm_server.sh` inside the container

## Troubleshooting

- Ensure your GPU drivers are properly installed and visible to Docker
- Check container logs with `docker-compose logs -f`
- For model download issues, verify your HF_TOKEN has access to the model
