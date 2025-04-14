#!/bin/bash
## This file is used to build a container from the ground up locally. NOT to use the published containers.
set -e

echo "🚀 Bridgy Setup Starting..."


INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$INSTALL_DIR/config"
ENV_FILE="$CONFIG_DIR/.env"
PEM_FILE="$CONFIG_DIR/intersight.pem"
IMAGE_NAME="bridgyv2-app"
REPO_URL="https://github.com/ciscoaiteam/bridgy-intersight-llm-demo.git"


# 1. Clone or update repo using token
#if [ ! -d "$INSTALL_DIR/.git" ]; then
#  echo "[+] Cloning Bridgy repo..."
#  git clone "$REPO_URL" "$INSTALL_DIR"
#else
#  echo "[i] Bridgy repo already exists at $INSTALL_DIR"
#  echo "[+] Pulling latest changes..."
#  cd "$INSTALL_DIR"
#  git pull "$REPO_URL"
#fi

cd "$INSTALL_DIR"

# 2. Create config directory
mkdir -p "$CONFIG_DIR"

# 3. Create .env template
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<EOF
# LangSmith Configuration
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT="bridgyv2"

# Intersight Configuration
INTERSIGHT_API_KEY=your_intersight_api_key_id_here
EOF
  echo "[+] .env template created at $ENV_FILE"
else
  echo "[i] .env file already exists at $ENV_FILE"
fi

# 4. Create PEM file template
if [ ! -f "$PEM_FILE" ]; then
  cat > "$PEM_FILE" <<EOF
-----BEGIN RSA PRIVATE KEY-----
Paste your Intersight PEM key here
-----END RSA PRIVATE KEY-----
EOF
  echo "[+] PEM template created at $PEM_FILE"
else
  echo "[i] PEM file already exists at $PEM_FILE"
fi

# 5. Prompt user to edit the files
echo
echo "✏️  Please edit the following files and add your credentials:"
echo "   $ENV_FILE"
echo "   $PEM_FILE"
read -p "🔄 Press [Enter] to continue after editing..."

# 6. Build Docker image
if docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "[i] Docker image '$IMAGE_NAME' already exists."
  read -p "🔁 Rebuild the image anyway? (y/N): " REBUILD
  if [[ "$REBUILD" =~ ^[Yy]$ ]]; then
    echo "[+] Rebuilding Docker image..."
    docker build -t "$IMAGE_NAME" .
  else
    echo "[✓] Skipping Docker build."
  fi
else
  echo "[+] Building Docker image for the first time..."
  docker build -t "$IMAGE_NAME" .
fi

# 7. Add alias to shell config
SHELL_RC="$HOME/.bashrc"
[ -n "$ZSH_VERSION" ] && SHELL_RC="$HOME/.zshrc"

ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        ALIAS_CMD="alias bridgy-start='docker run --rm -it --gpus all -v $CONFIG_DIR:/config --env-file /config/.env -p 8443:8443 $IMAGE_NAME'"
    else \
        ALIAS_CMD="alias bridgy-start='docker run --rm -it -v $CONFIG_DIR:/config --env-file /config/.env -p 8443:8443 $IMAGE_NAME'"
    fi

if ! grep -Fq "alias bridgy-start=" "$SHELL_RC"; then
  echo "$ALIAS_CMD" >> "$SHELL_RC"
  echo "[+] Added 'bridgy-start' alias to $SHELL_RC"
  echo "💡 Run 'source $SHELL_RC' or restart your terminal to use the shortcut."
else
  echo "[i] 'bridgy-start' alias already exists in $SHELL_RC"
fi

echo
echo "✅ Setup complete!"
echo "➡️  To start Bridgy, run:  bridgy-start"
