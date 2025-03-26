import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# LangSmith configuration
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "true")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "bridgyv2")

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def setup_langsmith():
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    if LANGSMITH_API_KEY:
        """Configure LangSmith environment variables"""
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = LANGSMITH_ENDPOINT
        os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
    else:
        # Optionally log a warning or set a dummy value
        os.environ["LANGCHAIN_API_KEY"] = ""
        print("Warning: LANGSMITH_API_KEY is not set. LangSmith features will be disabled.")
        os.environ["LANGCHAIN_ENDPOINT"] = ""
        os.environ["LANGCHAIN_PROJECT"] = ""