#!/bin/bash

set -e

echo "🚀 Bridgy Setup Starting..."

# Ensure GH_PAT is set
if [ -z "$GH_PAT" ]; then
  echo "❌ Environment variable GH_PAT is not set. Please export it:"
  echo "   export GH_PAT=your_personal_access_token"
  exit 1
fi

INSTALL_DIR="$HOME/bridgy"
IMAGE_NAME="bridgyv2-app"
REPO_URL="https://$GH_PAT@github.com/AMac00/bridgy.git"

# 1. Clone or update repo using token
if [ ! -d "$INSTALL_DIR" ]; then
  echo "[+] Cloning Bridgy repo..."
  git clone "$REPO_URL" "$INSTALL_DIR"
else
  echo "[i] Bridgy repo already exists at $INSTALL_DIR"
  echo "[+] Pulling latest changes..."
  cd "$INSTALL_DIR"
  git pull "https://$GH_PAT@github.com/AMac00/bridgy.git"
fi

cd "$INSTALL_DIR"

# 2. Prompt for LangSmith API Key (required)
echo
echo "🔐 Enter your LangSmith API key (required):"
read -r LANGSMITH_API_KEY
if [ -z "$LANGSMITH_API_KEY" ]; then
  echo "❌ LangSmith API Key is required. Exiting."
  exit 1
fi

# 3. Prompt for Intersight API Key (required)
echo "🔎 Enter your Intersight API key (required):"
read -r INTERSIGHT_API_KEY
if [ -z "$INTERSIGHT_API_KEY" ]; then
  echo "❌ Intersight API Key is required. Exiting."
  exit 1
fi

# 4. Write .env
cat > "$INSTALL_DIR/.env" <<EOF
# LangSmith Configuration
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="$LANGSMITH_API_KEY"
LANGSMITH_PROJECT="bridgyv2"

# Intersight (Required)
INTERSIGHT_API_KEY="$INTERSIGHT_API_KEY"
EOF

echo "[+] .env file created at $INSTALL_DIR/.env"

# 5. Check if Docker image exists
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

# 6. Add alias to shell config
SHELL_RC="$HOME/.bashrc"
[ -n "$ZSH_VERSION" ] && SHELL_RC="$HOME/.zshrc"

ALIAS_CMD="alias bridgy-start='docker run --rm -it --gpus all --env-file \$HOME/bridgy/.env -p 8443:8443 $IMAGE_NAME'"
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
