#!/bin/bash
# This file is copied in the container build process.
echo "[+] Starting Ollama..."
ollama serve &

sleep 5

echo "[+] Pulling models..."
ollama pull gemma2

echo "[+] Activating virtual environment..."
source /app/bridgy-main/venv/bin/activate

echo "[+] Launching Streamlit app..."
cd /app/bridgy-main
streamlit run --server.fileWatcherType none main.py --server.port 8443
