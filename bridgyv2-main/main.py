import os
import streamlit as st
import logging
from dotenv import load_dotenv
from experts.router import ExpertRouter
from utils.styling import apply_styling

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.debug("Starting Cisco Bridgy an AI Assistant")

# Load environment variables
load_dotenv()
logger.debug("Environment variables loaded")

# Initialize expert router
@st.cache_resource
def get_router():
    return ExpertRouter()

def main():
    # Apply custom styling
    apply_styling()

    # Set up the main layout
    st.title("Cisco Bridgy an AI Assistant")

    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "expert" in message:
                st.caption(f"Answered by: {message['expert']}")

    # Chat input
    if prompt := st.chat_input("Ask your question here..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get response from expert router
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    router = get_router()
                    response, expert = router.route_and_respond(prompt)
                    st.markdown(response)
                    st.caption(f"Answered by: {expert}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "expert": expert
                    })
                except Exception as e:
                    import traceback
                    error_traceback = traceback.format_exc()
                    logger.error(f"Error processing request: {str(e)}")
                    logger.debug(f"Detailed traceback: {error_traceback}")
                    
                    error_message = f"An error occurred: {str(e)}"
                    st.error(error_message)
                    
                    if st.checkbox("Show detailed error"):
                        st.code(error_traceback)
                        
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message,
                        "expert": "System"
                    })

if __name__ == "__main__":
    main()
