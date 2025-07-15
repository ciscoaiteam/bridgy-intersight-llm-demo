#!/bin/bash

# Bridgy OpenShift Deployment Script
# This script handles the complete deployment of Bridgy to OpenShift:
# - Creates secrets from .env and intersight.pem files
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
CERT_PATH="$PROJECT_ROOT/bridgy-main/cert.pem"
KEY_PATH="$PROJECT_ROOT/bridgy-main/key.pem"
SECRET_NAME="bridgy-secrets"
OUTPUT_FILE="$SCRIPT_DIR/bridgy-secrets.yaml"

# Use simple filenames for YAML resources with SCRIPT_DIR
BRIDGY_CONFIG="$SCRIPT_DIR/bridgy-optimized-deployment.yaml"
MONGODB_CONFIG="$SCRIPT_DIR/mongodb-deploymentconfig.yaml"
MONGODB_SERVICE="$SCRIPT_DIR/mongodb-service.yaml"
MONGODB_CONFIGMAP="$SCRIPT_DIR/mongodb-configmap.yaml"
MONGODB_INIT_CONFIGMAP="$SCRIPT_DIR/mongodb-init-configmap.yaml"
MONGODB_SA="$SCRIPT_DIR/mongodb-serviceaccount.yaml"
MONGODB_ROLEBINDING="$SCRIPT_DIR/mongodb-rolebinding.yaml"
BRIDGY_SERVICE="$SCRIPT_DIR/bridgy-main-service.yaml"
BRIDGY_ROUTE="$SCRIPT_DIR/bridgy-main-route.yaml"
BRIDGY_NODEPORT="$SCRIPT_DIR/bridgy-main-nodeport-service.yaml"
VLLM_SERVICE="$SCRIPT_DIR/vllm-service.yaml"
VLLM_DEPLOYMENT="$SCRIPT_DIR/vllm-deployment.yaml"
VLLM_MODELS_PVC="$SCRIPT_DIR/vllm-models-persistentvolumeclaim.yaml"
VLLM_HF_PVC="$SCRIPT_DIR/vllm-huggingface-persistentvolumeclaim.yaml"

# Check if files exist
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env file not found at $ENV_FILE"
  exit 1
fi

if [ ! -f "$PEM_FILE" ]; then
  echo "Error: intersight.pem file not found at $PEM_FILE"
  exit 1
fi

if [ ! -f "$BRIDGY_CONFIG" ]; then
  echo "Error: Bridgy configuration file not found at $BRIDGY_CONFIG"
  exit 1
fi

# Start creating the secret YAML file
cat > "$OUTPUT_FILE" << EOL
apiVersion: v1
kind: Secret
metadata:
  name: $SECRET_NAME
  labels:
    app: bridgy
type: Opaque
stringData:
EOL

# Check OpenShift login status
echo "Checking OpenShift login status..."
oc whoami &> /dev/null
if [ $? -ne 0 ]; then
  echo "Error: You are not logged into OpenShift. Please log in first using 'oc login'."
  exit 1
fi

# Check if current project is set
CURRENT_PROJECT=$(oc project -q 2>/dev/null)
if [ -z "$CURRENT_PROJECT" ]; then
  echo "Error: No OpenShift project is selected. Please select a project with 'oc project <project-name>'."
  exit 1
fi
echo "Using project: $CURRENT_PROJECT"

# Cleanup old bridgy-main resources
echo "Cleaning up old bridgy-main deployments, builds, and failed pods..."

# Function to safely execute commands with error handling
safe_execute() {
  echo "$ $@"
  "$@" || echo "Command failed with exit code $? (continuing anyway)"
}

# First, let's get the current active deployment
CURRENT_DC=$(oc get dc bridgy-main -o jsonpath='{.status.latestVersion}' 2>/dev/null || echo "0")
echo "Current active deployment is: bridgy-main-$CURRENT_DC"

# Clean up old replication controllers (which control the deployments)
echo "Removing old bridgy-main replication controllers..."
OLD_RCS=$(oc get rc -l app=bridgy-main | grep -v "NAME" | grep -v "bridgy-main-$CURRENT_DC" | awk '{print $1}' || true)
if [ -n "$OLD_RCS" ]; then
  echo "Found old replication controllers to clean up:"
  for rc in $OLD_RCS; do
    echo "Deleting RC: $rc"
    safe_execute oc delete rc $rc
  done
else
  echo "No old replication controllers found"
fi

# Clean up failed or completed bridgy-main deployment pods
echo "Removing old bridgy-main deployment pods..."
DEPLOY_PODS=$(oc get pods | grep "bridgy-main-.*-deploy" | grep -E "Completed|Error" | awk '{print $1}' || true)
if [ -n "$DEPLOY_PODS" ]; then
  echo "Found deployment pods to clean up:"
  for pod in $DEPLOY_PODS; do
    echo "Deleting deployment pod: $pod"
    safe_execute oc delete pod $pod --force --grace-period=0
  done
else
  echo "No old deployment pods found"
fi

# Clean up pods in CrashLoopBackOff state
echo "Removing bridgy-main pods in CrashLoopBackOff state..."
CRASHED_PODS=$(oc get pods | grep -E "bridgy-main" | grep -E "CrashLoopBackOff|Error|Completed" | grep -v "deploy" | grep -v "build" | awk '{print $1}' || true)
if [ -n "$CRASHED_PODS" ]; then
  echo "Found pods in problem state:"
  for pod in $CRASHED_PODS; do
    echo "Deleting problem pod: $pod"
    safe_execute oc delete pod $pod --force --grace-period=0
  done
else
  echo "No bridgy-main pods in problem state found"
fi

# Clean up any orphaned deployments
echo "Cleaning up orphaned deployments..."
ORPHANED_DEPLOYMENTS=$(oc get deployments -l app=bridgy-main 2>/dev/null | grep -v "NAME" | awk '{print $1}' || true)
if [ -n "$ORPHANED_DEPLOYMENTS" ]; then
  echo "Found orphaned deployments:"
  for dep in $ORPHANED_DEPLOYMENTS; do
    echo "Deleting deployment: $dep"
    safe_execute oc delete deployment $dep
  done
else
  echo "No orphaned deployments found"
fi

# Clean up old bridgy-main builds
echo "Removing old bridgy-main builds..."
# Keep the latest build, delete older ones
OLD_BUILDS=$(oc get builds -l buildconfig=bridgy-main | grep -v "NAME" | sort -rn | tail -n +2 | awk '{print $1}' || true)
if [ -n "$OLD_BUILDS" ]; then
  echo "Found old builds to clean up: $OLD_BUILDS"
  for build in $OLD_BUILDS; do
    safe_execute oc delete build $build
  done
else
  echo "No old builds found"
fi

# Parse .env file and add entries to the secret
echo "Adding environment variables from .env file..."
while IFS= read -r line || [[ -n "$line" ]]; do
  # Skip comments and empty lines
  if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
    continue
  fi

  # Extract key and value (handling both KEY=value and KEY="value" formats)
  if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
    key="${BASH_REMATCH[1]}"
    value="${BASH_REMATCH[2]}"

    # Remove quotes if present
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"

    # Convert to kebab-case for secret keys
    secret_key=$(echo "$key" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
    
    # Add to YAML with proper indentation
    echo "  $secret_key: \"$value\"" >> "$OUTPUT_FILE"
  fi
done < "$ENV_FILE"

# Add the intersight PEM file
echo "Adding Intersight PEM file..."
echo "  intersight-secret-key: |" >> "$OUTPUT_FILE"
while IFS= read -r line || [[ -n "$line" ]]; do
  echo "    $line" >> "$OUTPUT_FILE"
done < "$PEM_FILE"

echo "Secret YAML file created at: $OUTPUT_FILE"
echo "Applying secret to OpenShift cluster..."

# Apply the secret to the cluster
oc apply -f "$OUTPUT_FILE"

echo "Secret '$SECRET_NAME' created/updated successfully!"
echo ""

# Create MongoDB service account if it doesn't exist
echo "Setting up MongoDB service account..."
cat <<EOF | oc apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mongodb
  labels:
    app: mongodb
EOF

# Apply MongoDB rolebinding
echo "Creating MongoDB role binding..."
cat <<EOF | oc apply -f -
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: system:openshift:scc:anyuid
subjects:
  - kind: ServiceAccount
    name: mongodb
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:openshift:scc:anyuid
EOF

# Apply MongoDB resources first
echo "Applying MongoDB resources..."
oc apply -f "$MONGODB_CONFIGMAP"
oc apply -f "$MONGODB_INIT_CONFIGMAP"
oc apply -f "$MONGODB_SERVICE"
oc apply -f "$MONGODB_CONFIG"

# Apply MongoDB data PVC
MONGODB_DATA_PVC="$SCRIPT_DIR/mongodb-data-persistentvolumeclaim.yaml"
echo "Applying MongoDB data PVC..."
oc apply -f "$MONGODB_DATA_PVC"

# Wait for MongoDB to start
echo "Waiting for MongoDB to start..."
oc rollout status dc/mongodb --timeout=180s || echo "MongoDB rollout not completed within timeout, continuing anyway..."

# Check for and apply SSL certificates if they exist
echo "Checking for SSL certificates..."
SSL_CERTS_AVAILABLE=false

if [ -f "$CERT_PATH" ] && [ -f "$KEY_PATH" ]; then
  echo "SSL certificates found. Creating ConfigMaps..."
  
  # Create ConfigMaps from certificate files
  echo "Creating ConfigMap for SSL certificate..."
  oc create configmap bridgy-ssl-cert --from-file=cert.pem="$CERT_PATH" -o yaml --dry-run=client | oc apply -f -
  
  echo "Creating ConfigMap for SSL key..."
  oc create configmap bridgy-ssl-key --from-file=key.pem="$KEY_PATH" -o yaml --dry-run=client | oc apply -f -
  
  echo "SSL certificates deployed as ConfigMaps."
  SSL_CERTS_AVAILABLE=true
fi

# Apply SSL configuration if needed
if [ "$SSL_CERTS_AVAILABLE" = true ] || [ -f "$(dirname "$0")/bridgy-ssl-configmap.yaml" ]; then
  echo "Applying SSL configuration..."
  if [ -f "$(dirname "$0")/bridgy-ssl-configmap.yaml" ]; then
    oc apply -f "$(dirname "$0")/bridgy-ssl-configmap.yaml"
  fi
fi

# Apply vLLM resources if they exist
echo "Checking for vLLM resources..."
if [ -f "$VLLM_MODELS_PVC" ] && [ -f "$VLLM_HF_PVC" ] && [ -f "$VLLM_SERVICE" ] && [ -f "$VLLM_DEPLOYMENT" ]; then
  echo "vLLM resources found. Applying persistent volume claims..."
  oc apply -f "$VLLM_MODELS_PVC"
  oc apply -f "$VLLM_HF_PVC"
  
  echo "Applying vLLM service..."
  oc apply -f "$VLLM_SERVICE"
  
  # Parse .env file for HF_TOKEN if it exists
  if [ -f "$ENV_FILE" ]; then
    HF_TOKEN=$(grep 'HF_TOKEN=' "$ENV_FILE" | sed 's/HF_TOKEN=//' || echo "")
    if [ -n "$HF_TOKEN" ]; then
      echo "Found Hugging Face token in .env file. Updating secret..."
      oc patch secret "$SECRET_NAME" --type=merge -p "{\"stringData\":{\"hf-token\":\"$HF_TOKEN\"}}"
    else
      echo "No Hugging Face token found in .env file."
      echo "WARNING: Hugging Face token is required to download the Gemma 2 model."
      echo "Please create an .env file with HF_TOKEN=your_token or provide it via the --hf-token parameter."
      exit 1
    fi
  else
    echo "ERROR: .env file not found at $ENV_FILE"
    echo "Please create an .env file with HF_TOKEN=your_token or provide it via the --hf-token parameter."
    exit 1
  fi
  
  USE_VLLM=true
  echo "vLLM resources applied successfully."
else
  USE_VLLM=false
  echo "vLLM resources not found or incomplete. Skipping vLLM deployment."
fi

# Apply the Bridgy configuration
echo "Applying Bridgy optimized configuration with separated MongoDB..."
oc apply -f "$BRIDGY_CONFIG"

# Apply the NodePort service with correct selector
echo "Applying Bridgy NodePort service with correct selector..."
oc apply -f "$(dirname "$0")/bridgy-main-nodeport-service.yaml"

# Clean up any failed builds
echo "Cleaning up any previous failed builds..."
# Delete builds for bridgy-main
FAILED_BUILDS=$(oc get builds -l buildconfig=bridgy-main --no-headers | grep -E "Failed|Error|Cancelled" | awk '{print $1}' || true)
if [ -n "$FAILED_BUILDS" ]; then
  echo "Found failed builds to clean up: $FAILED_BUILDS"
  for build in $FAILED_BUILDS; do
    safe_execute oc delete build $build
  done
else
  echo "No failed builds found"
fi
# Delete build pods that belong to bridgy-main
BUILD_PODS=$(oc get pods -l buildconfig=bridgy-main --no-headers | awk '{print $1}' || true)
if [ -n "$BUILD_PODS" ]; then
  echo "Found build pods to clean up: $BUILD_PODS"
  for pod in $BUILD_PODS; do
    safe_execute oc delete pod $pod
  done
else
  echo "No build pods found"
fi

# Delete buildconfig to ensure we're using the latest
echo "Cleaning up existing buildconfig..."
if oc get buildconfig bridgy-main &> /dev/null; then
  safe_execute oc delete buildconfig bridgy-main
else
  echo "No existing buildconfig found"
fi

# Create a buildconfig inline since it may be missing after cleanup
echo "Creating bridgy-main buildconfig..."
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
EOF

# Create imagestream if it doesn't exist
echo "Creating imagestream if it doesn't exist..."
oc get imagestream bridgy-main || oc create imagestream bridgy-main

# Start the binary builds
echo ""
echo "Preparing source directory for binary build..."

# Create temporary directory for builds
BUILD_DIR=$(mktemp -d)
echo "Using temporary directory: $BUILD_DIR"

# Prepare bridgy-main build
echo "Preparing bridgy-main build..."
MAIN_DIR="$BUILD_DIR/bridgy-main-build"
mkdir -p "$MAIN_DIR"
cp -r "$(dirname "$0")/../bridgy-main" "$MAIN_DIR"
cp "$(dirname "$0")/../bridgy-main/Dockerfile" "$MAIN_DIR/Dockerfile"

# Make sure the scripts are executable
chmod +x "$MAIN_DIR/bridgy-main/verify_imports.py"
chmod +x "$MAIN_DIR/bridgy-main/optimized_init.sh"

# Start the build if it doesn't exist
if ! oc get builds -l buildconfig=bridgy-main | grep -q "bridgy-main-"; then
  echo "Starting new build for bridgy-main from directory $MAIN_DIR..."
  echo "This may take several minutes. Build logs will be displayed below:"
  oc start-build bridgy-main --from-dir="$MAIN_DIR" --follow --wait=true
else
  echo "Build already exists, not starting a new one"
fi

# Only build vLLM if we found the resources earlier
if [ "$USE_VLLM" = true ]; then
  # Check if vLLM buildconfig exists, clean up if needed
  echo "Checking for vLLM buildconfig..."
  
  # Clean up any failed vLLM builds
  FAILED_BUILDS=$(oc get builds -l buildconfig=vllm-server --no-headers | grep -E "Failed|Error|Cancelled" | awk '{print $1}' || true)
  if [ -n "$FAILED_BUILDS" ]; then
    echo "Found failed vLLM builds to clean up: $FAILED_BUILDS"
    for build in $FAILED_BUILDS; do
      safe_execute oc delete build $build
    done
  fi
  
  # Delete vLLM buildconfig to ensure we're using the latest
  echo "Cleaning up existing vLLM buildconfig..."
  if oc get buildconfig vllm-server &> /dev/null; then
    safe_execute oc delete buildconfig vllm-server
  else
    echo "No existing vLLM buildconfig found"
  fi
  
  # Create vLLM build directory
  VLLM_DIR="$BUILD_DIR/vllm"
  echo "Preparing vLLM build directory at $VLLM_DIR..."
  mkdir -p "$VLLM_DIR"
  
  # Copy vLLM files to build directory
  if [ -d "$PROJECT_ROOT/vllm" ]; then
    echo "Copying vLLM files from $PROJECT_ROOT/vllm/..."
    cp -r "$PROJECT_ROOT/vllm/"* "$VLLM_DIR/"
  else
    echo "ERROR: vLLM directory not found at $PROJECT_ROOT/vllm"
    echo "Please ensure the vllm directory exists in the project root."
    exit 1
  fi
  
  # Create vLLM buildconfig for binary build with build arg support
  echo "Creating vllm-server buildconfig with Hugging Face token support..."
  cat <<EOF | oc apply -f -
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: vllm-server
  labels:
    app: vllm-server
spec:
  failedBuildsHistoryLimit: 3
  successfulBuildsHistoryLimit: 3
  output:
    to:
      kind: ImageStreamTag
      name: vllm-server:latest
  source:
    type: Binary
    binary: {}
  strategy:
    type: Docker
    dockerStrategy:
      dockerfilePath: Dockerfile
      env:
        - name: HF_TOKEN
          value: "${HF_TOKEN}"
      buildArgs:
        - name: "HF_TOKEN"
          value: "${HF_TOKEN}"
  triggers:
    - type: ConfigChange
EOF

  # Create ImageStream if it doesn't exist
  if ! oc get imagestream vllm-server &> /dev/null; then
    echo "Creating ImageStream for vllm-server..."
    oc create imagestream vllm-server
  fi

  # Start the vLLM build using the binary build directory and pass HF_TOKEN as env var
  echo "Preparing vLLM build with Hugging Face authentication..."
  echo "Starting vllm-server build (this may take 15-30 minutes for model download)..."
  
  # Pass the Hugging Face token as an environment variable to the build
  oc start-build vllm-server --from-dir="$VLLM_DIR" \
    -e HF_TOKEN="$HF_TOKEN" \
    --follow --wait=true
  
  # Apply vLLM deployment after image is built
  echo "Applying vLLM deployment..."
  oc apply -f "$VLLM_DEPLOYMENT"
  
  echo "Waiting for vLLM deployment to start..."
  # This may timeout if the image is large and still pulling, that's ok
  oc rollout status deploymentconfig/vllm-server --timeout=180s || true
  
  # Update Bridgy to use vLLM if requested
  echo "Updating Bridgy to use vLLM server for local inference..."
  oc set env deploymentconfig/bridgy-main LLM_SERVICE_URL=http://vllm-server:8000/v1 LLM_MODEL=gemma-2-9b
fi

rm -rf "$BUILD_DIR"
echo "Cleaned up temporary build directories."

echo ""
echo "Deployment initiated successfully!"
echo "You can monitor the build status with:"
echo "  oc get builds"
echo "  oc get pods"

# Wait for a moment and then show the build status
sleep 5
echo ""
echo "Current build status:"
oc get builds

echo ""
echo "Current pods:"
oc get pods

echo ""
echo "Services:"
oc get services | grep bridgy

echo ""
echo "Routes:"
oc get routes | grep bridgy

echo ""
echo "Deployment process has been started. The application will be available"
echo "once the builds complete and the pods are running."
echo "You can continue monitoring with: oc get pods -w"
