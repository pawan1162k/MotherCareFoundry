import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from utils.logger import setup_logger

# Inject the CSS once
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Call it at the top of your main function
local_css("streamlit/assets/style.css")

logger = setup_logger("interface")

st.set_page_config(page_title="Patient Diagnosis App", layout="wide")

def main():
    st.title("Patient Diagnosis App")
    st.write("Please complete the steps below to receive a diagnosis.")

    # Sidebar navigation is handled by Streamlit's multi-page app
    st.sidebar.title("Navigation")
    st.sidebar.write("Select a step to proceed.")

if __name__ == "__main__":
    main()