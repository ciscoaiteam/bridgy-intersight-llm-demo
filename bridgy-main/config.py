import os
from dotenv import load_dotenv

# Use a single location for .env file - project root
ENV_FILE_PATH = "/.env"  # Absolute path from project root

def load_environment():
    """Load environment variables from the .env file in project root"""
    # Get the absolute path to the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Full path to the .env file
    env_path = os.path.join(project_root, ".env")
    
    # Load from the .env file
    if os.path.exists(env_path):
        try:
            load_dotenv(dotenv_path=env_path)
            print(f"[INFO] Successfully loaded .env from {env_path}")
            return True, env_path
        except Exception as e:
            print(f"[WARNING] Failed to load .env: {str(e)}")
    else:
        print(f"⚠️  No .env file found at {env_path}")
        print(f"Please copy .env_example to {env_path}")
    
    return False, None

# Load environment variables at module import time
loaded, env_path = load_environment()

# LangSmith configuration
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "true")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "bridgy")

# Intersight config
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "bridgy")


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