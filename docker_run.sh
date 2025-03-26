#!/bin/bash

set -e

echo "🚀 Bridgy Setup Starting..."

INSTALL_DIR="$HOME/bridgy"
ENV_FILE="$INSTALL_DIR/.env"
IMAGE_NAME="ghcr.io/amac00/bridgyv2-app:latest"

# 1. Ensure GH_PAT is set
if [ -z "$GH_PAT" ]; then
  echo "❌ Environment variable GH_PAT is not set. Please export it:"
  echo "   export GH_PAT=your_personal_access_token"
  exit 1
fi

mkdir -p "$INSTALL_DIR"

# 2. Prompt for LangSmith API Key (required)
echo
echo "🔐 Enter your LangSmith API key (required):"
read -r LANGSMITH_API_KEY
if [ -z "$LANGSMITH_API_KEY" ]; then
  echo "❌ LangSmith API Key is required. Exiting."
  exit 1
fi

# 3. Prompt for Intersight API Key ID
echo
echo "🔎 Enter your Intersight API Key ID (required):"
read -r INTERSIGHT_API_KEY_ID
if [ -z "$INTERSIGHT_API_KEY_ID" ]; then
  echo "❌ Intersight API Key ID is required. Exiting."
  exit 1
fi

# 3.2 Prompt for PEM Key (multiline)
echo
echo "🔐 Paste your full Intersight PEM Private Key below (end with CTRL+D):"
INTERSIGHT_PEM_KEY=$(</dev/stdin)
if [ -z "$INTERSIGHT_PEM_KEY" ]; then
  echo "❌ Intersight PEM Private Key is required. Exiting."
  exit 1
fi

# 4. Write .env file
cat > "$ENV_FILE" <<EOF
# LangSmith Configuration
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="$LANGSMITH_API_KEY"
LANGSMITH_PROJECT="bridgyv2"

# Intersight
INTERSIGHT_API_KEY_ID="$INTERSIGHT_API_KEY_ID"
$INTERSIGHT_PEM_KEY="$INTERSIGHT_PEM_KEY"
EOF

echo "[+] .env file created at $ENV_FILE"

# 5. Docker login and pull image
echo
echo "🔐 Logging in to GitHub Container Registry..."
echo "$GH_PAT" | docker login ghcr.io -u your_github_username --password-stdin

echo "📦 Pulling Bridgy Docker image from GHCR..."
docker pull "$IMAGE_NAME"

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
