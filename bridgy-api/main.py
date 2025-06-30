import os
import httpx # Changed from requests for async support
import logging
import json # For WebSocket message parsing
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator, ValidationError
from typing import List, Literal, Dict
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration ---
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/chat")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "gemma2")

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Ollama Chat API",
    description="API to interact with an Ollama instance for chat.",
    version="0.1.0",
)

# --- CORS Configuration ---
# Adjust origins as needed for production
origins = [
    "*", # Allow all origins for development - BE CAREFUL IN PRODUCTION
    # "http://localhost:3000", # Example for a React frontend
    # "your_frontend_domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)

# --- Pydantic Models for Request/Response Validation ---
class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    model: str = Field(default=DEFAULT_MODEL, description="The Ollama model to use.")
    messages: List[Message] = Field(..., description="Conversation history including the latest message.")

class ChatResponse(BaseModel):
    reply: str

# --- Custom Exceptions for Ollama Service ---
class OllamaServiceError(Exception):
    """Base exception for Ollama service issues."""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

class OllamaTimeoutError(OllamaServiceError):
    """Exception for Ollama API timeouts."""
    def __init__(self, message="Ollama API request timed out"):
        super().__init__(message, status_code=504)

class OllamaRequestError(OllamaServiceError):
    """Exception for general Ollama API request failures."""
    def __init__(self, message="Failed to connect to Ollama service"): # Default message updated
        super().__init__(message, status_code=503)

class OllamaProcessingError(OllamaServiceError):
    """Exception for errors processing Ollama's response."""
    def __init__(self, message="Error processing Ollama response"):
        super().__init__(message, status_code=500)

# --- API Routes ---
@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Health check endpoint for Kubernetes probes."""
    return {"status": "healthy"}

@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_handler(chat_request: ChatRequest):
    """
    Handles chat requests by forwarding them to the Ollama API.
    """

    # Unique identifier for this request, useful for tracing logs
    request_id = f"http-{os.urandom(4).hex()}"
    logger.info(f"[{request_id}] HTTP: Received chat request for model: {chat_request.model} with {len(chat_request.messages)} messages.")

    messages_dict_list = [msg.dict() for msg in chat_request.messages]

    try:
        reply = await _get_ollama_reply(chat_request.model, messages_dict_list, client_identifier=request_id)
        logger.info(f"[{request_id}] HTTP: Successfully processed chat request for model: {chat_request.model}. Reply length: {len(reply)}")
        return ChatResponse(reply=reply)
    except OllamaServiceError as e:
        logger.error(f"[{request_id}] HTTP: Ollama service error for model {chat_request.model}: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e: # Catch-all for unexpected errors not originating from _get_ollama_reply
        logger.error(f"[{request_id}] HTTP: An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

async def _get_ollama_reply(model: str, messages_dict_list: List[Dict], client_identifier: str) -> str:
    """
    Helper function to communicate with the Ollama API.
    `client_identifier` is used for logging purposes.
    """
    logger.info(f"[{client_identifier}] Requesting Ollama. Model: {model}, Messages count: {len(messages_dict_list)}")
    ollama_payload = {
        "model": model,
        "messages": messages_dict_list,
        "stream": False
    }
    logger.debug(f"[{client_identifier}] Sending payload to Ollama: {ollama_payload}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(OLLAMA_API_URL, json=ollama_payload, timeout=60)
            response.raise_for_status() # Raise HTTPStatusError for bad responses (4xx or 5xx)
            ollama_data = response.json()
            reply_content = ollama_data.get('message', {}).get('content') # Explicitly get content

            if reply_content is None: # Check if content is None (e.g. key exists but value is null)
                logger.warning(f"[{client_identifier}] Ollama response 'content' is missing or null. Full response: {ollama_data}")
                raise OllamaProcessingError("Ollama response did not contain valid content.")
            
            logger.info(f"[{client_identifier}] Successfully processed Ollama request for model: {model}. Reply length: {len(reply_content)}")
            return reply_content
        except httpx.TimeoutException:
            logger.error(f"[{client_identifier}] Ollama API request timed out after 60 seconds.")
            raise OllamaTimeoutError()
        except httpx.HTTPStatusError as e:
            logger.error(f"[{client_identifier}] Ollama API request failed with status {e.response.status_code}: {e.response.text}")
            raise OllamaRequestError(f"Ollama service returned an error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e: # Covers other network issues like connection errors
            logger.error(f"[{client_identifier}] Ollama API request failed: {e}")
            raise OllamaRequestError(f"Failed to connect to Ollama service: {e}")
        except json.JSONDecodeError as e: # If Ollama returns non-JSON response
            logger.error(f"[{client_identifier}] Failed to decode JSON response from Ollama: {e}")
            raise OllamaProcessingError(f"Invalid JSON response from Ollama: {e}")
        except Exception as e: # Catch other unexpected errors during Ollama interaction
            logger.error(f"[{client_identifier}] An unexpected error occurred while interacting with Ollama: {e}", exc_info=True)
            raise OllamaProcessingError(f"An unexpected error occurred with Ollama: {e}")

@app.websocket("/ws/chat")
async def websocket_chat_handler(websocket: WebSocket):
    await websocket.accept()
    client_addr = f"{websocket.client.host}:{websocket.client.port}"
    ws_session_id = f"ws-{client_addr}-{os.urandom(4).hex()}" # Unique ID for this WebSocket session/connection
    logger.info(f"[{ws_session_id}] WebSocket: Client connected.")
    
    active_model = DEFAULT_MODEL # To store model for logging in case of errors before model is parsed
    try:
        while True:
            try:
                data_str = await websocket.receive_text()
                client_request_data = json.loads(data_str)

                chat_request_ws = ChatRequest(**client_request_data)
                active_model = chat_request_ws.model # Update active model for this message
                messages_dict_list = [msg.dict() for msg in chat_request_ws.messages]
                
                request_id = f"{ws_session_id}-msg-{os.urandom(2).hex()}" # Unique ID for this specific message
                logger.info(f"[{request_id}] WebSocket: Received request for model: {active_model} with {len(messages_dict_list)} messages.")

                reply = await _get_ollama_reply(active_model, messages_dict_list, client_identifier=request_id)
                await websocket.send_json({"reply": reply})
                logger.info(f"[{request_id}] WebSocket: Sent reply for model {active_model}. Reply length: {len(reply)}")

            except (json.JSONDecodeError, ValidationError) as e:
                error_detail = e.errors() if isinstance(e, ValidationError) else str(e)
                logger.warning(f"[{ws_session_id}] WebSocket: Invalid data from client: {error_detail}")
                await websocket.send_json({"error": "Invalid data format", "details": error_detail})
            except OllamaServiceError as e:
                logger.error(f"[{ws_session_id}] WebSocket: Ollama service error for model {active_model}: {e}")
                await websocket.send_json({"error": str(e), "status_code": e.status_code})
            except Exception as e: # Catch other unexpected errors during message processing
                logger.error(f"[{ws_session_id}] WebSocket: Error processing message for model {active_model}: {e}", exc_info=True)
                await websocket.send_json({"error": "An internal server error occurred while processing your message."})

    except WebSocketDisconnect:
        logger.info(f"[{ws_session_id}] WebSocket: Client disconnected.")
    except Exception as e: # Catch errors during initial connection or WebSocket loop setup
        logger.error(f"[{ws_session_id}] WebSocket: Unhandled exception in WebSocket handler: {e}", exc_info=True)
        # Attempt to close gracefully if possible, FastAPI might handle this too
        if websocket.client_state != httpx. पता_नहीं: # Check if client_state is available and not closed
             await websocket.close(code=1011) # Internal Error

# --- Running the App (using uvicorn) ---
# You would typically run this using the command line:
# uvicorn main:app --reload --host 0.0.0.0 --port 5000
#
# if __name__ == "__main__":
#     import uvicorn
#     # This is mainly for debugging within an IDE, not recommended for production
#     uvicorn.run(app, host="127.0.0.1", port=5000)
