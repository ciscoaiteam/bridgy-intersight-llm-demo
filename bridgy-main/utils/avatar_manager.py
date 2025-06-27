import os
import streamlit as st

def avatar_settings():
    """Display the fixed avatars from the avatars folder"""
    st.sidebar.title("Avatar Settings")

    avatars_dir = "avatars"
    if not os.path.exists(avatars_dir):
        os.makedirs(avatars_dir)

    user_avatar_path = os.path.join(avatars_dir, "user.jpg")
    assistant_avatar_path = os.path.join(avatars_dir, "assistant.png")

    # Display user avatar
    st.sidebar.subheader("User Avatar")
    if os.path.exists(user_avatar_path):
        st.sidebar.image(user_avatar_path, width=100)
    else:
        st.sidebar.warning("user.jpg not found in avatars folder")

    # Display assistant avatar
    st.sidebar.subheader("Assistant Avatar")
    if os.path.exists(assistant_avatar_path):
        st.sidebar.image(assistant_avatar_path, width=100)
    else:
        st.sidebar.warning("assistant.png not found in avatars folder")