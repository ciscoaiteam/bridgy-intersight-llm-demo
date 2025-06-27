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
    .stMarkdown h1, .stMarkdown h1 {
        color: #049fd9;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 10px;
    }
    .stMarkdown h2, .stMarkdown h2 {
        color: #049fd9;
        font-weight: bold;
        margin-top: 16px;
        margin-bottom: 8px;
    }
    .stMarkdown h3, .stMarkdown h3 {
        color: #444;
        font-weight: bold;
        margin-top: 12px;
        margin-bottom: 6px;
    }
    .stMarkdown p, .stMarkdown p {
        margin-bottom: 10px;
        line-height: 1.5;
    }
    .stMarkdown ul, .stMarkdown ul {
        margin-bottom: 10px;
        margin-left: 20px;
    }
    .stMarkdown ol, .stMarkdown ol {
        margin-bottom: 10px;
        margin-left: 20px;
    }
    .stMarkdown li, .stMarkdown li {
        margin-bottom: 5px;
    }
    .stMarkdown table, .stMarkdown table {
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 15px;
    }
    .stMarkdown th, .stMarkdown th {
        background-color: #f1f1f1;
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    .stMarkdown td, .stMarkdown td {
        border: 1px solid #ddd;
        padding: 8px;
    }
    .stMarkdown tr:nth-child(even), .stMarkdown tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .stMarkdown code, .stMarkdown code {
        background-color: #f6f8fa;
        padding: 3px 5px;
        border-radius: 3px;
        font-family: monospace;
    }
    .stMarkdown a, .stMarkdown a {
        color: #0366d6;
        text-decoration: none;
    }
    .stMarkdown a:hover, .stMarkdown a:hover {
        text-decoration: underline;
    }
    .stMarkdown small, .stMarkdown small {
        font-size: 85%;
        color: #6c757d;
    }
    </style>
    """, unsafe_allow_html=True)
