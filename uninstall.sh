#!/bin/bash

set -e

INSTALL_DIR="$HOME/bridgy"
IMAGE_NAME="bridgy-app"

echo "⚠️  This will remove Bridgy, its Docker image, and related setup."

read -p "Are you sure you want to continue? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "Cancelled."
  exit 0
fi

# 1. Remove Docker container (if running)
CONTAINER_ID=$(docker ps -aqf "ancestor=$IMAGE_NAME")
if [ -n "$CONTAINER_ID" ]; then
  echo "[+] Stopping container: $CONTAINER_ID"
  docker stop "$CONTAINER_ID" >/dev/null
fi

# 2. Remove Docker image
if docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "[+] Removing Docker image: $IMAGE_NAME"
  docker rmi "$IMAGE_NAME"
else
  echo "[i] Docker image $IMAGE_NAME not found."
fi

# 3. Remove bridgy folder
if [ -d "$INSTALL_DIR" ]; then
  echo "[+] Deleting project folder: $INSTALL_DIR"
  rm -rf "$INSTALL_DIR"
else
  echo "[i] Project folder $INSTALL_DIR not found."
fi

# 4. Remove alias from shell config
SHELL_RC="$HOME/.bashrc"
[ -n "$ZSH_VERSION" ] && SHELL_RC="$HOME/.zshrc"

if grep -q "alias bridgy-start=" "$SHELL_RC"; then
  sed -i '/alias bridgy-start=/d' "$SHELL_RC"
  echo "[+] Removed bridgy-start alias from $SHELL_RC"
else
  echo "[i] No alias found in $SHELL_RC"
fi

echo "✅ Uninstallation complete. You may want to run: source $SHELL_RC"
