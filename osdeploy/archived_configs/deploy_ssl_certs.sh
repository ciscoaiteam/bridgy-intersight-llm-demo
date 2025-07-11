#!/bin/bash

# Script to deploy SSL certificates as ConfigMaps for bridgy-main

# Path to certificate files (relative to project root)
CERT_PATH="../cert.pem"
KEY_PATH="../key.pem"

# Check if certificate files exist
if [ ! -f "$CERT_PATH" ]; then
    echo "Error: Certificate file not found at $CERT_PATH"
    exit 1
fi

if [ ! -f "$KEY_PATH" ]; then
    echo "Error: Key file not found at $KEY_PATH"
    exit 1
fi

# Create ConfigMaps from certificate files
echo "Creating ConfigMap for SSL certificate..."
oc create configmap bridgy-ssl-cert --from-file=cert.pem="$CERT_PATH" -o yaml --dry-run=client | oc apply -f -

echo "Creating ConfigMap for SSL key..."
oc create configmap bridgy-ssl-key --from-file=key.pem="$KEY_PATH" -o yaml --dry-run=client | oc apply -f -

echo "SSL certificates deployed as ConfigMaps."
