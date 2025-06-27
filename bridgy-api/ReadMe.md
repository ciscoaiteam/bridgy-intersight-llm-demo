# FastAPI Ollama Chat Backend

This is a basic FastAPI backend template designed to interact with an Ollama instance for multi-turn chat conversations. It serves as an API for a frontend application (e.g., React).

## Prerequisites

*   Python 3.8+
*   pip
*   A running Ollama instance (accessible at `http://localhost:11434` by default)
*   An Ollama model pulled (e.g., `ollama pull llama3`)

## Setup

1.  **Environment Variables:** Create a `.env` file (or set environment variables) for `OLLAMA_API_URL` and `DEFAULT_MODEL`. See `.env.example` if provided, or the top of `main.py`.

2.  **Clone the repository (or create the project files):**
    ```bash
    git clone <your-repo-url> # Or manually create the files
    cd <your-project-directory>
    ```

3.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

Use Uvicorn to run the FastAPI application:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
The API will be available at http://0.0.0.0:5000 (or http://127.0.0.1:5000). The --reload flag automatically restarts the server when code changes are detected (useful for development).

Project Structure
plaintext
your-project-directory/
├── venv/                  # Virtual environment directory
├── main.py                # Main FastAPI application file
├── requirements.txt       # Python package dependencies
├── .env                   # Local environment variables (optional, gitignored)
└── README.md              # This file
API Endpoint
POST /api/chat: Sends a message and conversation history to Ollama and receives a response.
Request Body (JSON):
json
{
  "model": "llama3", // Or your desired Ollama model
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Why is the sky blue?"},
    {"role": "assistant", "content": "The sky appears blue due to a phenomenon called Rayleigh scattering..."},
    {"role": "user", "content": "What about sunsets?"}
  ]
}
Response Body (JSON):
json
{
  "reply": "Sunsets often appear red or orange because..."
}
// Or an error message (e.g., 422, 500, 503, 504)
{
    "detail": "Description of the error"
}
API Documentation (Auto-Generated)
FastAPI automatically generates interactive API documentation. Once the application is running, access them at:

Swagger UI: http://127.0.0.1:5000/docs
ReDoc: http://127.0.0.1:5000/redoc