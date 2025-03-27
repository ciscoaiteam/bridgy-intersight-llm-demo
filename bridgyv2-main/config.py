import os
from dotenv import load_dotenv

# Prefer the Docker-mounted config path
docker_env_path = "/config/.env"
local_env_path = "./.env"

# Check if the Docker-mounted .env exists
if os.path.exists(docker_env_path):
    load_dotenv(dotenv_path=docker_env_path)
    print("Found {0}.".format(docker_env_path))
    print(f"[INFO] Loaded .env from {docker_env_path}")
elif os.path.exists(local_env_path):
    load_dotenv(dotenv_path=local_env_path)
    print(f"[INFO] Loaded .env from {local_env_path}")
    print("Print config direcotry")
    for root, dirs, files in os.walk(docker_env_path):
        for file in files:
            print(os.path.join(root, file))
else:
    print("⚠️  No .env file found in either /config/ or current directory.")

# LangSmith configuration
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "true")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "bridgyv2")

# Intersight config
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "bridgyv2")


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