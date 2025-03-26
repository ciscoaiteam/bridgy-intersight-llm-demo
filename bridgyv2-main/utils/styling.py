
import streamlit as st

def apply_styling():
    """Apply custom styling to the Streamlit app"""
    # Custom CSS
    st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .stHeader {
        background-color: #049fd9;
        color: white;
    }
    .stMarkdown h1 {
        color: #049fd9;
    }
    .stMarkdown h2 {
        color: #049fd9;
    }
    </style>
    """, unsafe_allow_html=True)
