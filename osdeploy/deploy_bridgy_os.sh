#!/bin/bash

# Bridgy Complete OpenShift Deployment Script
# This script handles the complete deployment of Bridgy ecosystem to OpenShift:
# - Creates secrets from .env and intersight.pem files
# - Deploys vLLM server with Gemma 2 support and GPU acceleration
# - Applies MongoDB resources separately (ConfigMap, Service, Deployment)
# - Applies Bridgy configuration that connects to the separate MongoDB
# - Starts build for bridgy-main using the optimized Dockerfile
# - Monitors build and deployment progress

set -e  # Exit on error

# Set up paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
NAMESPACE="demo1"
ENV_FILE="$PROJECT_ROOT/.env"
PEM_FILE="$PROJECT_ROOT/bridgy-main/intersight.pem"
SECRET_NAME="bridgy-secrets"
OUTPUT_FILE="$SCRIPT_DIR/bridgy-secrets.yaml"

# Deployment files
BRIDGY_CONFIG="$SCRIPT_DIR/bridgy-optimized-deployment.yaml"
MONGODB_CONFIG="$SCRIPT_DIR/mongodb-deploymentconfig.yaml"
MONGODB_SERVICE="$SCRIPT_DIR/mongodb-service.yaml"
MONGODB_CONFIGMAP="$SCRIPT_DIR/mongodb-configmap.yaml"
MONGODB_INIT_CONFIGMAP="$SCRIPT_DIR/mongodb-init-configmap.yaml"
MONGODB_SA="$SCRIPT_DIR/mongodb-serviceaccount.yaml"
MONGODB_ROLEBINDING="$SCRIPT_DIR/mongodb-rolebinding.yaml"
BRIDGY_NODEPORT="$SCRIPT_DIR/bridgy-main-nodeport-service.yaml"
VLLM_COMPLETE_DEPLOYMENT="$SCRIPT_DIR/vllm-complete-deployment.yaml"

# Parse command-line options
ONLY_VLLM=false
ONLY_FRONTEND=false
CLEANUP_FIRST=false
HF_TOKEN_CLI=""

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy Bridgy ecosystem to OpenShift with optional component selection"
    echo ""
    echo "Options:"
    echo "  --only-vllm      Deploy only vLLM components (skip MongoDB and Bridgy frontend)"
    echo "  --only-frontend  Deploy only frontend components (skip vLLM)"
    echo "  --cleanup        Clean up existing deployments before deploying"
    echo "  --hf-token TOKEN Hugging Face token for model download"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Full deployment (MongoDB + vLLM + Bridgy)"
    echo "  $0 --only-frontend           # Deploy only MongoDB + Bridgy (no vLLM)"
    echo "  $0 --only-vllm               # Deploy only vLLM server"
    echo "  $0 --hf-token YOUR_TOKEN     # Provide HF token via command line"
}

cleanup_existing_deployments() {
    echo "🧹 Cleaning up existing deployments..."
    
    # Clean up vLLM deployments and pods
    echo "  🤖 Cleaning up vLLM resources..."
    oc delete dc vllm-server --ignore-not-found=true
    oc delete pods -l app=vllm-server --force --grace-period=0 --ignore-not-found=true
    
    # Clean up any old vLLM fixed deployments
    oc delete dc vllm-server-fixed --ignore-not-found=true
    oc delete pods -l app=vllm-server-fixed --force --grace-period=0 --ignore-not-found=true
    
    # Clean up Bridgy main deployments (but keep frontend for continuity)
    echo "  🌉 Cleaning up Bridgy main builds..."
    oc delete pods -l app=bridgy-main --field-selector=status.phase=Failed --force --grace-period=0 --ignore-not-found=true
    oc delete pods -l app=bridgy-main --field-selector=status.phase=Error --force --grace-period=0 --ignore-not-found=true
    
    # Clean up any pending/stuck builds
    echo "  🔨 Cleaning up failed builds..."
    oc get builds --no-headers | grep -E "(Failed|Error|Cancelled)" | awk '{print $1}' | xargs -r oc delete builds --ignore-not-found=true
    
    # Wait a moment for resources to be cleaned up
    echo "  ⏳ Waiting for cleanup to complete..."
    sleep 10
    
    echo "✅ Cleanup completed"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --only-vllm)
      ONLY_VLLM=true
      shift
      ;;
    --only-frontend)
      ONLY_FRONTEND=true
      shift
      ;;
    --cleanup)
      CLEANUP_FIRST=true
      shift
      ;;
    --hf-token)
      HF_TOKEN_CLI="$2"
      shift 2
      ;;
    --help)
      show_help
      exit 0
      ;;
    *)
      echo "❌ Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Print deployment mode
if [ "$ONLY_VLLM" = true ]; then
  echo "🚀 Running in vLLM-only mode - will only deploy vLLM components"
elif [ "$ONLY_FRONTEND" = true ]; then
  echo "🚀 Running in frontend-only mode - will only deploy frontend components"
else
  echo "🚀 Running in full deployment mode - deploying all components"
fi

# Function to safely execute commands with error handling
safe_execute() {
  echo "$ $@"
  "$@" || echo "⚠️ Command failed with exit code $? (continuing anyway)"
}

# Check OpenShift login status
echo "🔍 Checking OpenShift login status..."
if ! oc whoami &> /dev/null; then
  echo "❌ Error: You are not logged into OpenShift. Please log in first using 'oc login'."
  exit 1
fi

# Check if current project is set
CURRENT_PROJECT=$(oc project -q 2>/dev/null)
if [ -z "$CURRENT_PROJECT" ]; then
  echo "❌ Error: No OpenShift project is selected. Please select a project with 'oc project <project-name>'."
  exit 1
fi
echo "✅ Using project: $CURRENT_PROJECT"

# Clean up existing deployments if requested
if [ "$CLEANUP_FIRST" = true ]; then
  cleanup_existing_deployments
fi

# Check if files exist (skip for vLLM-only mode)
if [ "$ONLY_VLLM" = false ]; then
  if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: .env file not found at $ENV_FILE"
    exit 1
  fi

  if [ ! -f "$PEM_FILE" ]; then
    echo "❌ Error: intersight.pem file not found at $PEM_FILE"
    exit 1
  fi

  if [ ! -f "$BRIDGY_CONFIG" ]; then
    echo "❌ Error: Bridgy configuration file not found at $BRIDGY_CONFIG"
    exit 1
  fi
fi

# Create secrets
echo "🔐 Creating Kubernetes secrets..."

# Start creating the secret YAML file
cat > "$OUTPUT_FILE" << 'EOL'
apiVersion: v1
kind: Secret
metadata:
  name: bridgy-secrets
  labels:
    app: bridgy
type: Opaque
stringData:
EOL

# Add content to the secret based on available files
if [ "$ONLY_VLLM" = false ]; then
  # Add .env file contents
  echo "  📝 Adding .env variables to secret..."
  while IFS= read -r line; do
    if [[ $line =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      key=$(echo "$line" | cut -d'=' -f1)
      value=$(echo "$line" | sed 's/^[^=]*=//' | sed 's/"//g' | sed "s/'//g")
      echo "  $key: \"$value\"" >> "$OUTPUT_FILE"
    fi
  done < "$ENV_FILE"
  
  # Add intersight.pem file content
  echo "  📝 Adding intersight.pem to secret..."
  echo "  intersight.pem: |" >> "$OUTPUT_FILE"
  sed 's/^/    /' "$PEM_FILE" >> "$OUTPUT_FILE"
fi

# Add HF token if provided via CLI or found in .env
HF_TOKEN="$HF_TOKEN_CLI"
if [ -z "$HF_TOKEN" ] && [ -f "$ENV_FILE" ]; then
  HF_TOKEN=$(grep 'HF_TOKEN=' "$ENV_FILE" | sed 's/HF_TOKEN=//' | sed 's/"//g' | sed "s/'//g" || echo "")
fi

if [ -n "$HF_TOKEN" ]; then
  echo "  📝 Adding HF token to secret..."
  echo "  hf-token: \"$HF_TOKEN\"" >> "$OUTPUT_FILE"
fi

# Apply the secret
echo "🔐 Applying secrets to OpenShift..."
oc apply -f "$OUTPUT_FILE"

# Deploy MongoDB if not in vLLM-only mode
if [ "$ONLY_VLLM" = false ]; then
  echo "🗄️ Deploying MongoDB..."
  
  # Apply MongoDB resources
  if [ -f "$MONGODB_SA" ]; then
    echo "👤 Setting up MongoDB service account..."
    oc apply -f "$MONGODB_SA"
  fi
  
  if [ -f "$MONGODB_ROLEBINDING" ]; then
    echo "🔒 Creating MongoDB role binding..."
    oc apply -f "$MONGODB_ROLEBINDING"
  fi
  
  if [ -f "$MONGODB_CONFIGMAP" ]; then
    echo "⚙️ Applying MongoDB ConfigMap..."
    oc apply -f "$MONGODB_CONFIGMAP"
  fi
  
  if [ -f "$MONGODB_INIT_CONFIGMAP" ]; then
    echo "🔧 Applying MongoDB init ConfigMap..."
    oc apply -f "$MONGODB_INIT_CONFIGMAP"
  fi
  
  if [ -f "$MONGODB_SERVICE" ]; then
    echo "🔌 Applying MongoDB service..."
    oc apply -f "$MONGODB_SERVICE"
  fi
  
  if [ -f "$MONGODB_CONFIG" ]; then
    echo "🚀 Applying MongoDB deployment..."
    oc apply -f "$MONGODB_CONFIG"
    
    # Wait for MongoDB to start
    echo "⏳ Waiting for MongoDB to start..."
    oc rollout status deployment/mongodb --timeout=180s || echo "⚠️ MongoDB rollout not completed within timeout, continuing anyway..."
  fi
fi

# Deploy vLLM Server if not in frontend-only mode
if [ "$ONLY_FRONTEND" = false ]; then
  echo "🤖 Deploying vLLM Server with Gemma 2 support..."
  
  # Check if the consolidated vLLM deployment file exists
  if [ -f "$VLLM_COMPLETE_DEPLOYMENT" ]; then
    echo "📝 Found vLLM complete deployment file"
    
    # Ensure HF token is available for vLLM
    if [ -z "$HF_TOKEN" ]; then
      echo "❌ ERROR: Hugging Face token is required for vLLM deployment"
      echo "Please provide HF_TOKEN via --hf-token parameter or in .env file"
      exit 1
    fi
    
    # Apply the complete vLLM deployment
    echo "🚀 Deploying vLLM server with GPU acceleration..."
    oc apply -f "$VLLM_COMPLETE_DEPLOYMENT"
    
    # Wait for vLLM deployment to be ready
    echo "⏳ Waiting for vLLM deployment to complete (this may take some time for model download)..."
    oc rollout status dc/vllm-server --timeout=1800s || echo "⚠️ vLLM deployment timeout - check logs for progress"
    
    # Check final status
    echo "🔍 Checking vLLM pod status..."
    oc get pods -l app=vllm-server
    
    # Get route if it exists
    VLLM_ROUTE=$(oc get route vllm-server -o jsonpath='{.spec.host}' 2>/dev/null || echo "")
    if [ -n "$VLLM_ROUTE" ]; then
      echo "🌐 vLLM Server URL: https://$VLLM_ROUTE"
      echo "📚 API Docs: https://$VLLM_ROUTE/docs"
      echo "🔍 Models endpoint: https://$VLLM_ROUTE/v1/models"
    else
      echo "📝 Use port-forward to access: oc port-forward svc/vllm-server 8000:8000"
    fi
    
    echo "✅ vLLM deployment completed successfully!"
  else
    echo "⚠️ vLLM deployment file not found at $VLLM_COMPLETE_DEPLOYMENT"
    echo "Skipping vLLM deployment."
  fi
else
  echo "⚙️ Skipping vLLM deployment (frontend-only mode)"
fi

# Deploy Bridgy frontend if not in vLLM-only mode
if [ "$ONLY_VLLM" = false ]; then
  echo "🌐 Deploying Bridgy frontend..."
  
  # Apply the Bridgy configuration
  echo "🚀 Applying Bridgy optimized configuration..."
  oc apply -f "$BRIDGY_CONFIG"

  # Apply the NodePort service
  if [ -f "$BRIDGY_NODEPORT" ]; then
    echo "🔌 Applying Bridgy NodePort service..."
    oc apply -f "$BRIDGY_NODEPORT"
  fi

  # Clean up any failed builds
  echo "🧹 Cleaning up any previous failed builds..."
  FAILED_BUILDS=$(oc get builds -l buildconfig=bridgy-main --no-headers | grep -E "Failed|Error|Cancelled" | awk '{print $1}' || true)
  if [ -n "$FAILED_BUILDS" ]; then
    echo "Found failed builds to clean up: $FAILED_BUILDS"
    for build in $FAILED_BUILDS; do
      safe_execute oc delete build $build
    done
  fi

  # Clean up build pods
  BUILD_PODS=$(oc get pods -l buildconfig=bridgy-main --no-headers | awk '{print $1}' || true)
  if [ -n "$BUILD_PODS" ]; then
    echo "Cleaning up build pods: $BUILD_PODS"
    for pod in $BUILD_PODS; do
      safe_execute oc delete pod $pod
    done
  fi

  # Delete existing buildconfig to ensure we're using the latest
  if oc get buildconfig bridgy-main &> /dev/null; then
    safe_execute oc delete buildconfig bridgy-main
  fi

  # Create buildconfig
  echo "🔨 Creating bridgy-main buildconfig..."
  cat <<EOF | oc apply -f -
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: bridgy-main
  labels:
    app: bridgy-main
spec:
  source:
    type: Binary
  strategy:
    type: Docker
    dockerStrategy:
      dockerfilePath: Dockerfile
  output:
    to:
      kind: ImageStreamTag
      name: bridgy-main:latest
  triggers:
  - type: ConfigChange
EOF

  # Create imagestream if it doesn't exist
  if ! oc get imagestream bridgy-main &> /dev/null; then
    echo "📦 Creating ImageStream for bridgy-main..."
    oc create imagestream bridgy-main
  fi

  # Start the build
  echo "🔨 Starting Bridgy build..."
  echo "Preparing frontend source for build..."
  cd "$PROJECT_ROOT/bridgy-main"
  
  # Make sure scripts are executable
  chmod +x verify_imports.py optimized_init.sh 2>/dev/null || true
  
  # Start binary build
  oc start-build bridgy-main --from-dir=. --follow --wait
  
  echo "⏳ Waiting for deployment to complete..."
  oc rollout status dc/bridgy-main --timeout=300s
  
  echo "✅ Bridgy frontend deployment completed!"
else
  echo "⚙️ Skipping Bridgy frontend deployment (vLLM-only mode)"
fi

# Final status summary
echo ""
echo "🎉 Deployment Summary"
echo "===================="

if [ "$ONLY_VLLM" = false ]; then
  echo "📊 MongoDB Status:"
  oc get pods -l app=mongodb | head -2
  
  echo ""
  echo "🌐 Bridgy Frontend Status:"
  oc get pods -l app=bridgy-main | head -2
  
  # Get Bridgy route
  BRIDGY_ROUTE=$(oc get route bridgy-main -o jsonpath='{.spec.host}' 2>/dev/null || echo "")
  if [ -n "$BRIDGY_ROUTE" ]; then
    echo "🔗 Bridgy URL: https://$BRIDGY_ROUTE"
  fi
fi

if [ "$ONLY_FRONTEND" = false ]; then
  echo ""
  echo "🤖 vLLM Server Status:"
  oc get pods -l app=vllm-server | head -2
  
  VLLM_ROUTE=$(oc get route vllm-server -o jsonpath='{.spec.host}' 2>/dev/null || echo "")
  if [ -n "$VLLM_ROUTE" ]; then
    echo "🔗 vLLM URL: https://$VLLM_ROUTE"
  fi
fi

echo ""
echo "📖 Useful commands:"
echo "  🔍 Check all pods: oc get pods"
echo "  📋 Check logs: oc logs -l app=<app-name> -f"
echo "  🌐 Get routes: oc get routes"
echo "  🔧 Port forward: oc port-forward svc/<service-name> <local-port>:<remote-port>"

echo ""
echo "✅ Deployment completed successfully!"
