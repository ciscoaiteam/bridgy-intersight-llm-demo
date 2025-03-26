#!/bin/bash

echo "[+] Starting Ollama..."
ollama serve &

sleep 5

echo "[+] Pulling Mistral model..."
ollama pull gemma2

echo "[+] Activating virtual environment..."
source /app/bridgyv2-main/venv/bin/activate

echo "[+] Launching Streamlit app..."
cd /app/bridgyv2-main
streamlit run --server.fileWatcherType none main.py --server.port 8443
