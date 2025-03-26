
# Cisco Bridgy AI Assistant

A Streamlit-based application that uses LLMs to answer questions about Cisco infrastructure, specializing in Intersight, AI Pods, and general Cisco knowledge.

## Overview

Cisco Bridgy is an AI assistant that routes queries to specialized experts:

- **Intersight Expert**: Answers questions about server inventory, status, and infrastructure management
- **AI Pods Expert**: Provides information about Cisco AI Pods, their documentation, and LLM hardware requirements
- **General Expert**: Handles general Cisco knowledge questions

## Setup Instructions for Linux

### Prerequisites

- Python 3.11 or higher
- cuDNN 9+ for FAISS CPU-Support
- Internet connectivity
- OpenAI API key
- Intersight API key (for Intersight-related queries)
### Installation Steps

1. **Clone or download the repository**

   Download the application code to your Linux machine.

2. **Install dependencies**

   ```bash
   # Install required system packages
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-dev build-essential libssl-dev zlib1g-dev libjpeg-dev libtiff-dev
   
   # Install application dependencies
   pip install faiss-cpu langchain-community langchain openai python-dotenv streamlit tiktoken intersight trafilatura langchain-openai pillow pypdf
   ```

3. **Set up environment variables**

   Create a `.env` file in the root directory with the following variables:

   ```
   OPENAI_API_KEY=your_openai_api_key
   LANGSMITH_API_KEY=your_langsmith_api_key  # Optional, for tracing
   LANGSMITH_PROJECT=bridgyv2  # Optional, for tracing
   INTERSIGHT_API_KEY=your_intersight_api_key_id  # Required for Intersight functionality
   ```

4. **Configure Intersight API credentials**

   If you plan to use the Intersight Expert functionality, you'll need:
   
   - Add your Intersight API Key ID to the `.env` file as shown above
   - Place your Intersight Secret Key in the root directory as `intersight_secret_key.pem`
   
   You can generate these credentials from your Intersight account under Settings > API Keys.

## Running the Application

1. **Start the Streamlit application**

   ```bash
   streamlit run main.py --server.port 8443
   streamlit run --server.fileWatcherType none main.py --server.port 8443
   ```

2. **Access the application**

   Open a web browser and navigate to:
   - `http://0.0.0.0:8443` (if accessing locally)
   - `http://your_server_ip:8443` (if accessing from another machine)

## Project Structure

```
├── .streamlit/                # Streamlit configuration
├── experts/                   # Expert modules
│   ├── ai_pods_expert.py      # AI Pods expert implementation
│   ├── general_expert.py      # General Cisco knowledge expert
│   ├── intersight_expert.py   # Intersight expert implementation
│   └── router.py              # Expert routing logic
├── pdf/                       # Documentation PDFs
├── tools/                     # Utility tools
│   ├── intersight_api.py      # Intersight API interface
│   └── pdf_loader.py          # PDF document loader
├── utils/                     # Utility functions
│   ├── avatar_manager.py      # Chat avatar management
│   └── styling.py             # UI styling utilities
├── config.py                  # Application configuration
├── main.py                    # Main application entry point
└── .env                       # Environment variables (create this)
```

## Usage

1. After starting the application, you'll see the Cisco Bridgy AI Assistant interface.
2. Type your question in the chat input at the bottom of the screen.
3. The assistant will automatically route your question to the appropriate expert and display the response.
4. Questions about your Intersight environment, AI Pods, or general Cisco knowledge are all supported.

## Troubleshooting

- **Port access issues**: If you can't access the application from another machine, check your firewall settings to ensure port 5000 is open.
- **API connection errors**: Ensure your OpenAI API key and Intersight credentials are correctly configured.
- **Missing dependencies**: Run `pip install -r requirements.txt` to ensure all required packages are installed.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| OPENAI_API_KEY | Your OpenAI API key | Yes |
| LANGSMITH_API_KEY | LangSmith API key for tracing | No |
| LANGSMITH_PROJECT | LangSmith project name | No |
| LANGSMITH_TRACING | Enable/disable tracing (true/false) | No |
| LANGSMITH_ENDPOINT | LangSmith API endpoint | No |

## License

[Include license information here]

## Contributors

[List contributors here]
