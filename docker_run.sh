#!/bin/bash
# The start script to deploy the service from the Repo container.
# Fill out the .env and PEM files before running.
set -e

echo "🚀 Bridgy Setup Starting..."

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$INSTALL_DIR/config"
ENV_FILE="$CONFIG_DIR/.env"
PEM_FILE="$CONFIG_DIR/intersight.pem"
IMAGE_NAME="ghcr.io/amac00/bridgyv2-app:latest"

mkdir -p "$CONFIG_DIR"

# 2. Create .env template if missing
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

# 3. Create PEM file if missing
if [ ! -f "$PEM_FILE" ]; then
  cat > "$PEM_FILE" <<EOF
-----BEGIN RSA PRIVATE KEY-----
Paste your PEM-formatted key here
-----END RSA PRIVATE KEY-----
EOF
  echo "[+] PEM template created at $PEM_FILE"
else
  echo "[i] PEM file already exists at $PEM_FILE"
fi

# 4. Prompt user to edit the files
echo
echo "✏️  Please edit the following files and fill in your credentials:"
echo "   $ENV_FILE"
echo "   $PEM_FILE"
read -p "🔄 Press [Enter] to continue after editing the files..."

# 5. Docker login and pull image
echo
echo "🔐 Logging in to GitHub Container Registry..."
echo "$GH_PAT" | docker login ghcr.io -u your_github_username --password-stdin

echo "📦 Pulling Bridgy Docker image from GHCR..."
docker pull "$IMAGE_NAME"

# 6. Add alias to shell config
SHELL_RC="$HOME/.bashrc"
[ -n "$ZSH_VERSION" ] && SHELL_RC="$HOME/.zshrc"

ALIAS_CMD="alias bridgy-start='docker run --rm -it --gpus all -v $CONFIG_DIR:/config --env-file /config/.env -p 8443:8443 $IMAGE_NAME'"
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
