#!/bin/bash

# Build and Deploy React App to OpenShift
# Usage: ./deploy.sh [environment] [image-tag]

set -e

ENVIRONMENT=${1:-dev}
IMAGE_TAG=${2:-latest}
APP_NAME="react-app"
REGISTRY="your-openshift-registry"
PROJECT_NAME="your-project-${ENVIRONMENT}"

echo "🚀 Building and deploying React app to OpenShift..."
echo "Environment: ${ENVIRONMENT}"
echo "Image Tag: ${IMAGE_TAG}"
echo "Project: ${PROJECT_NAME}"

# Login to OpenShift (if not already logged in)
# oc login --token=<your-token> --server=<your-server>

# Switch to the correct project
echo "📁 Switching to project: ${PROJECT_NAME}"
oc project ${PROJECT_NAME} || oc new-project ${PROJECT_NAME}

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t ${REGISTRY}/${PROJECT_NAME}/${APP_NAME}:${IMAGE_TAG} .

# Push the image to the registry
echo "📤 Pushing image to registry..."
docker push ${REGISTRY}/${PROJECT_NAME}/${APP_NAME}:${IMAGE_TAG}

# Update the deployment YAML with the correct image
echo "📝 Updating deployment configuration..."
sed -i "s|your-registry/react-app:latest|${REGISTRY}/${PROJECT_NAME}/${APP_NAME}:${IMAGE_TAG}|g" deployment.yaml

# Apply the Kubernetes manifests
echo "🚀 Deploying to OpenShift..."
oc apply -f deployment.yaml

# Wait for deployment to complete
echo "⏳ Waiting for deployment to complete..."
oc rollout status deployment/${APP_NAME} --timeout=300s

# Get the route URL
echo "🌐 Getting application URL..."
ROUTE_URL=$(oc get route ${APP_NAME}-route -o jsonpath='{.spec.host}')
echo "✅ Application deployed successfully!"
echo "🔗 Access your app at: https://${ROUTE_URL}"

# Show deployment status
echo "📊 Deployment Status:"
oc get pods -l app=${APP_NAME}
oc get svc -l app=${APP_NAME}
oc get route -l app=${APP_NAME}