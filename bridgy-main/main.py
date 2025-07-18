from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_serializer, ConfigDict
from typing import Dict, List, Optional, Tuple, Any, Annotated
import uuid
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import time
import random
from dotenv import load_dotenv
from experts.router import ExpertRouter
import ssl
import motor.motor_asyncio
from bson import ObjectId
import asyncio
import re


# Test 

def setup_logging():
    """Configure logging with daily log rotation."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure the root logger
    root_logger = logging.getLogger()  # Root logger
    root_logger.setLevel(logging.DEBUG)

    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create handlers
    stream_handler = logging.StreamHandler()  # For console output

    # Use TimedRotatingFileHandler for daily log rotation
    file_handler = TimedRotatingFileHandler(
        "logs/bridgy_api.log",
        when="midnight",  # Rotate at midnight
        interval=1,       # Interval of 1 day
        backupCount=7,    # Keep 7 backup log files
        encoding="utf-8"
    )

    error_handler = TimedRotatingFileHandler(
        "logs/bridgy_api_errors.log",
        when="midnight",  # Rotate at midnight
        interval=1,       # Interval of 1 day
        backupCount=7,    # Keep 7 backup log files
        encoding="utf-8"
    )

    # Customize the rotated filenames to include the date
    file_handler.suffix = "%Y-%m-%d"
    error_handler.suffix = "%Y-%m-%d"

    # Set log levels
    stream_handler.setLevel(logging.DEBUG)  # All logs to the console
    file_handler.setLevel(logging.INFO)     # General logs
    error_handler.setLevel(logging.ERROR)   # Errors only

    # Create a formatter and attach it to the handlers
    formatter = logging.Formatter(log_format)
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)

    # Add handlers to the root logger
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    # Ensure all child loggers propagate to the root logger
    # This makes sure module-specific loggers inherit the root logger's configuration
    logging.getLogger("experts").setLevel(logging.DEBUG)
    logging.getLogger("experts").propagate = True

    return root_logger

# Initialize logging
logger = setup_logging()
logger.info("Starting Cisco Bridgy AI Assistant API server...")

# Add this after setup_logging() in main.py
logger.info("Main logger test")
logging.getLogger("experts.router").error("Test from experts.router logger")

# Load environment variables
load_dotenv()
logger.debug("Environment variables loaded")

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
DB_NAME = os.getenv("MONGODB_DB", "bridgy_db")
THREADS_COLLECTION = "threads"
MESSAGES_COLLECTION = "messages"

# Initialize MongoDB client
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]

# Create FastAPI app
app = FastAPI(title="Cisco Bridgy AI Assistant API", version="1.0.0")

# Log startup
logger.debug("Debug logging enabled")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("CORS middleware configured")

# Initialize the expert router (with singleton pattern)
_expert_router = None

def get_expert_router():
    global _expert_router
    if _expert_router is None:
        from experts.router import ExpertRouter
        _expert_router = ExpertRouter()
    return _expert_router

# Pydantic models compatible with Pydantic V2
class ThreadCreate(BaseModel):
    threadName: str = Field(..., min_length=1)

class ThreadResponse(BaseModel):
    threadId: str

class MessageCreate(BaseModel):
    threadId: str
    message: str
    autoInvokedCommand: bool = False

class MessageResponse(BaseModel):
    content: str
    url: str
    timestamp: int
    id: str
    followUps: List[str]
    expert: str

class ThreadModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    
    id: Optional[ObjectId] = Field(default=None, alias="_id")
    threadId: str
    threadName: str
    createdAt: str
    
    @field_serializer('id')
    def serialize_id(self, id: Optional[ObjectId]) -> Optional[str]:
        return str(id) if id else None

class MessageModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    
    id: Optional[ObjectId] = Field(default=None, alias="_id")
    messageId: str
    threadId: str
    userMessage: str
    assistantMessage: str
    expert: str
    timestamp: str
    autoInvokedCommand: bool = False
    
    @field_serializer('id')
    def serialize_id(self, id: Optional[ObjectId]) -> Optional[str]:
        return str(id) if id else None

# Helper functions
def generate_id() -> str:
    return str(uuid.uuid4())

def get_timestamp() -> str:
    return int(time.time() * 1000)

def get_unix_timestamp() -> int:
    return int(time.time() * 1000)

async def generate_follow_ups(original_message: str, response: str, expert: str) -> List[str]:
    """Generate follow-up questions based on the conversation using the ExpertRouter"""
    try:
        # Create a prompt for generating follow-up questions
        follow_up_prompt = f"""
            Based on the following conversation, generate 2 specific follow-up questions that would be helpful for the user to ask next.
            Make the questions concise, specific, and directly related to the conversation content.

            User question: {original_message}

            Assistant response (by {expert}): {response}

            Generate exactly 2 follow-up questions:
            """
        
        # Use the ExpertRouter to generate follow-up questions
        router = get_expert_router()
        follow_up_response, _ = router.route_and_respond(follow_up_prompt)
        
        # Parse the response to extract the follow-up questions
        potential_questions = [
            line.strip() for line in follow_up_response.split('\n') 
            if line.strip() and ('?' in line or line.strip().startswith('1.') or line.strip().startswith('2.'))
        ]
        
        # Clean up the questions (remove numbers, etc.)
        cleaned_questions = []
        for q in potential_questions:
            # Remove leading numbers and symbols
            cleaned_q = q.strip()
            if cleaned_q.startswith(('1.', '2.', '3.', '-', '*', '•')):
                cleaned_q = cleaned_q[2:].strip()
            cleaned_questions.append(cleaned_q)
        
        # Ensure we have at least 2 questions
        if len(cleaned_questions) >= 2:
            return cleaned_questions[:2]  # Return exactly 2 questions
        
        logger.warning(f"LLM didn't generate enough follow-up questions, adding fallback options")
        
        # If we don't have enough, add some generic ones
        generic_fallbacks = [
            "Can you explain that in more detail?",
            "What are the implications of this?",
            "How does this relate to other Cisco technologies?",
            "Can you provide a practical example?"
        ]
        
        while len(cleaned_questions) < 2:
            # Add generic questions until we have 2
            for q in generic_fallbacks:
                if q not in cleaned_questions:
                    cleaned_questions.append(q)
                    break
                    
        return cleaned_questions[:2]
        
    except Exception as e:
        logger.error(f"Error generating follow-up questions: {str(e)}", exc_info=True)
        # Fallback to generic questions if there's an error
        generic_followups = [
            "Can you explain that in more detail?",
            "What are the implications of this?",
            "How does this relate to other Cisco technologies?",
            "Can you provide an example?"
        ]
        return random.sample(generic_followups, 2)


# API Endpoints

# Serve static files from the 'pdf' directory at /pdf
app.mount("/pdf", StaticFiles(directory="pdf"), name="pdf")


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Cisco Bridgy AI Assistant API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    
    # Check MongoDB connection
    mongo_status = "connected"
    try:
        # Ping the database
        await db.command("ping")
    except Exception as e:
        mongo_status = "disconnected"
        logger.error(f"MongoDB connection error: {str(e)}")
    
    # Check if expert router can be initialized
    expert_status = "connected"
    try:
        router = get_expert_router()
    except Exception as e:
        expert_status = "disconnected"
        logger.warning(f"Expert router check failed: {str(e)}")
    
    health_data = {
        "status": "healthy",
        "mongodb": mongo_status,
        "expert_router": expert_status,
        "timestamp": get_timestamp()
    }
    logger.info(f"Health check completed: {health_data}")
    return health_data

@app.post("/api/threads", response_model=ThreadResponse)
async def create_thread(thread_data: ThreadCreate):
    """
    Create a new thread.
    Expects JSON payload with threadName field.
    """
    try:
        logger.debug(f"Received thread creation request for thread name: '{thread_data.threadName}'")
        
        thread_id = generate_id()
        timestamp = get_timestamp()
        
        thread_doc = {
            "threadId": thread_id,
            "threadName": thread_data.threadName,
            "dateModified": timestamp
        }
        
        # Store thread in MongoDB
        await db[THREADS_COLLECTION].insert_one(thread_doc)
        
        logger.info(f"Successfully created thread with ID: {thread_id} and name: '{thread_data.threadName}'")
        
        return ThreadResponse(threadId=thread_id)
    
    except Exception as e:
        logger.error(f"Error creating thread with name '{thread_data.threadName}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create thread: {str(e)}")

@app.post("/api/threads/{thread_id}/messages", response_model=MessageResponse)
async def send_message(thread_id: str, message_data: MessageCreate):
    """Send a message to a thread and get expert response"""
    logger.info(f"Received message for thread: {thread_id}")
    logger.debug(f"Message data: {message_data}")
    
    # Check if thread exists
    thread = await db[THREADS_COLLECTION].find_one({"threadId": thread_id})
    if not thread:
        logger.warning(f"Thread not found: {thread_id}")
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Validate that threadId in payload matches URL parameter
    if message_data.threadId != thread_id:
        logger.error(f"Thread ID mismatch: URL={thread_id}, Body={message_data.threadId}")
        raise HTTPException(status_code=400, detail="Thread ID mismatch")
    
    try:
        logger.info(f"Routing message to expert: {message_data.message[:50]}...")
        
        # Use the ExpertRouter to get a response
        try:
            router = get_expert_router()
            response, expert = router.route_and_respond(message_data.message)
            logger.info(f"Response received from expert: {expert}")
        except Exception as e:
            logger.error(f"Error from expert router: {str(e)}", exc_info=True)
            response = f"I'm sorry, I encountered an error while processing your request: {str(e)}"
            expert = "System"
        
        # Generate follow-up suggestions
        follow_ups = await generate_follow_ups(message_data.message, response, expert)
        
        # Create message record for MongoDB
        message_id = generate_id()
        timestamp = get_timestamp()
        unix_timestamp = get_unix_timestamp()
        
        '''
            Mark Down / Other stuff formating for AI Assistant
    
        '''
        #Update response formating for Cisco AI-Assistant UI 
        formatted_response = re.sub(r'\n{2,}', '<br>', response)
        # Find references to PDF files in the response and convert them to hyperlinks
        # formatted_response = re.sub(
        #     r'pdf/([a-zA-Z0-9_\-\.]+\.pdf)', 
        #     r'<a href="/api/docs/\1" target="_blank">pdf/\1</a>', 
        #     formatted_response
        # )
        # Make the Expert Bold
        # formatted_response = re.sub(r'href=\\"pdf/', r'href=\\"https://64.101.226.221:8443/pdf/', formatted_response)
        formatted_response = "{0} <br><br> Response Provided by <br> ** {1} **".format(formatted_response, expert)
        formatted_response = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', formatted_response)


        # Store Uwer and System Response
        message_doc = {
            "messageId": message_id,
            "threadId": thread_id,
            "userMessage": message_data.message,
            "assistantMessage": formatted_response,
            "expert": expert,
            "timestamp": timestamp,
            "autoInvokedCommand": message_data.autoInvokedCommand
        }
        
        # Store message in MongoDB
        await db[MESSAGES_COLLECTION].insert_one(message_doc)
        
        logger.info(f"Successfully processed message for thread {thread_id}")
        logger.debug(f"Response length: {len(response)} characters")
        
        # Return the expected response format
        return MessageResponse(
            content=formatted_response,
            url="https://64.101.226.223:30843/api",  # HTTPS URL - customize as needed
            timestamp=unix_timestamp,
            id=message_id,
            followUps=follow_ups,
            expert=expert
        )
        
    except Exception as e:
        logger.error(f"Failed to process message for thread {thread_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")

@app.get("/api/threads")
async def get_threads():
    """Get all threads"""
    logger.info("Retrieving all threads")
    
    try:
        # Retrieve threads from MongoDB
        cursor = db[THREADS_COLLECTION].find().sort("dateModified", -1)  # Sort by creation date, newest first
        threads = await cursor.to_list(length=100)  # Limit to 100 threads
        
        logger.info(f"Retrieved {len(threads)} threads")
        
        # Convert ObjectId to string for JSON serialization
        for thread in threads:
            thread["_id"] = str(thread["_id"])
        
        return {"items": threads}
    except Exception as e:
        logger.error(f"Error retrieving threads: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve threads: {str(e)}")

@app.get("/api/threads/{thread_id}/messages")
async def get_thread(thread_id: str):
    """Get specific thread with its messages"""
    logger.info(f"Retrieving thread: {thread_id}")
    try:
        # Get thread information
        thread = await db[THREADS_COLLECTION].find_one({"threadId": thread_id})
        if not thread:
            logger.warning(f"Thread not found: {thread_id}")
            raise HTTPException(status_code=404, detail="Thread not found")
        # Convert ObjectId to string
        thread["_id"] = str(thread["_id"])
        # Get messages for this thread
        cursor = db[MESSAGES_COLLECTION].find({"threadId": thread_id}).sort("timestamp", 1)  # Sort by timestamp
        messages = await cursor.to_list(length=1000)  # Limit to 1000 messages per thread
        
        # Format messages as separate user and assistant items
        formatted_messages = []
        for message in messages:
            # Add user message
            formatted_messages.append({
                "sender": "USER",
                "content": message["userMessage"],
                "timestamp": int(message["timestamp"].timestamp() * 1000) if isinstance(message["timestamp"], datetime) else int(message["timestamp"]),
                "id": message.get("messageId", str(message["_id"]))
            })
            
            # Add assistant message
            formatted_messages.append({
                "sender": "SYSTEM",
                "content": message["assistantMessage"],
                "timestamp": int(message["timestamp"].timestamp() * 1000) if isinstance(message["timestamp"], datetime) else int(message["timestamp"]) + 1,  # Add 1ms to ensure chronological order
                "id": f"{message.get('messageId', str(message['_id']))}_response"
            })
        
        logger.info(f"Thread found with {len(formatted_messages)} formatted messages")
        return {
            "items": formatted_messages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving thread {thread_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve thread: {str(e)}")

@app.delete("/api/threads/{thread_id}")
async def delete_thread(thread_id: str):
    """Delete a thread and all its associated messages"""
    logger.info(f"Deleting thread: {thread_id}")
    
    try:
        # Check if thread exists
        thread = await db[THREADS_COLLECTION].find_one({"threadId": thread_id})
        if not thread:
            logger.warning(f"Thread not found: {thread_id}")
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Delete thread from database
        thread_result = await db[THREADS_COLLECTION].delete_one({"threadId": thread_id})
        
        # Delete all messages associated with this thread
        message_result = await db[MESSAGES_COLLECTION].delete_many({"threadId": thread_id})
        
        logger.info(f"Successfully deleted thread {thread_id} and {message_result.deleted_count} associated messages")
        
        return {
            "success": True,
            "threadId": thread_id,
            "messagesDeleted": message_result.deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting thread {thread_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete thread: {str(e)}")

@app.get("/api/docs")
async def list_documents():
    """List all documents in the docs folder"""
    logger.info("Listing documents from docs folder")
    try:
        docs_dir = os.path.join(os.path.dirname(__file__), "pdf")
        if not os.path.exists(docs_dir):
            logger.warning(f"Docs directory not found: {docs_dir}")
            return {"documents": []}
        
        # Get all files in the docs directory
        files = []
        for file in os.listdir(docs_dir):
            file_path = os.path.join(docs_dir, file)
            if os.path.isfile(file_path):
                # Get file size and last modified time
                stat_info = os.stat(file_path)
                files.append({
                    "filename": file,
                    "size": stat_info.st_size,
                    "last_modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                    "url": f"/api/docs/{file}"
                })
        
        logger.info(f"Found {len(files)} documents in pdf folder")
        return {"documents": files}
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.get("/api/docs/{filename}")
async def download_document(filename: str):
    """Download a specific document from the docs folder"""
    logger.info(f"Request to download document: {filename}")
    try:
        # Sanitize filename to prevent directory traversal attacks
        filename = os.path.basename(filename)
        docs_dir = os.path.join(os.path.dirname(__file__), "pdf")
        file_path = os.path.join(docs_dir, filename)
        
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            logger.warning(f"Document not found: {filename}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        logger.info(f"Serving document: {filename}")
        return FileResponse(
            path=file_path, 
            filename=filename,
            media_type="application/octet-stream"  # This will force download
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document {filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to download document: {str(e)}")

@app.get("/api/experts")
async def get_experts():
    """Get available experts"""
    try:
        router = get_expert_router()
        # Assuming ExpertRouter has a way to get experts (you may need to add this)
        experts = router.get_experts() if hasattr(router, 'get_experts') else []
        return {"experts": experts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get experts: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Check if we need to install MongoDB dependencies
    try:
        import motor.motor_asyncio
    except ImportError:
        logger.error("MongoDB driver (motor) not installed. Please install it with:")
        logger.error("pip install motor")
        exit(1)
        
    logger.info("Initializing FastAPI server with HTTPS...")
    
    # Check if SSL certificate files exist
    cert_file = "cert.pem"
    key_file = "key.pem"
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        # Start server with HTTPS
        uvicorn.run(
            "main:app", 
            host="0.0.0.0", 
            port=8443, 
            ssl_keyfile=key_file,
            ssl_certfile=cert_file,
            reload=True
        )
        logger.info("Server started with HTTPS on port 8443")
    else:
        logger.warning(f"SSL certificate files not found: {cert_file} and/or {key_file}")
        logger.warning("Starting server without HTTPS")
        # Start without HTTPS as fallback
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
        logger.info("Server started without HTTPS on port 8000")