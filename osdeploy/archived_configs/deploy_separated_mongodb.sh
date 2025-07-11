#!/bin/bash

# Bridgy OpenShift Deployment Script (Updated for Separated MongoDB)
# This script handles the complete deployment of Bridgy to OpenShift:
# - Creates secrets from .env and intersight.pem files
# - Applies MongoDB resources (ConfigMap, Service, Deployment)
# - Applies Bridgy main application with separate MongoDB
# - Starts build for bridgy-main
# - Monitors build and deployment progress

set -e  # Exit on error

# Paths
ENV_FILE="../.env"
PEM_FILE="../intersight.pem"
SECRET_NAME="bridgy-secrets"
OUTPUT_FILE="./bridgy-secrets.yaml"
BRIDGY_CONFIG="./bridgy-separated-mongodb.yaml"

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
oc apply -f "$(dirname "$0")/mongodb-configmap.yaml"
oc apply -f "$(dirname "$0")/mongodb-init-configmap.yaml"
oc apply -f "$(dirname "$0")/mongodb-service.yaml"
oc apply -f "$(dirname "$0")/mongodb-deploymentconfig.yaml"

# Wait for MongoDB to start
echo "Waiting for MongoDB to start..."
oc rollout status deployment/mongodb --timeout=180s

# Apply SSL configuration if it exists
if [ -f "$(dirname "$0")/bridgy-ssl-configmap.yaml" ]; then
  echo "Applying SSL configuration..."
  oc apply -f "$(dirname "$0")/bridgy-ssl-configmap.yaml"
fi

# Apply the Bridgy configuration
echo "Applying Bridgy configuration with separated MongoDB..."
oc apply -f "$BRIDGY_CONFIG"

# Clean up any failed builds
echo "Cleaning up any previous failed builds..."
oc delete builds -l openshift.io/build-config.name=bridgy-main --ignore-not-found=true
oc delete pods -l openshift.io/build.name --ignore-not-found=true

# Delete buildconfigs to ensure we're using the latest
oc delete buildconfig bridgy-main --ignore-not-found=true

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

# Start the build with binary source
echo ""
echo "Starting build for bridgy-main..."
oc start-build bridgy-main --from-dir="$MAIN_DIR" --follow

# Clean up temp directory
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
oc get services

echo ""
echo "Routes:"
oc get routes

echo ""
echo "Deployment process has been started. The application will be available"
echo "once the builds complete and the pods are running."
echo "You can continue monitoring with: oc get pods -w"
