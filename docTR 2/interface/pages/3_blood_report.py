import streamlit as st
import tempfile
import os  # ADDED: Missing import
from utils.logger import setup_logger
from data_extraction.ocr import extract_report
from storage.chroma_db import add_to_health_history

logger = setup_logger("blood_report")

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("streamlit/assets/style.css")

def save_uploaded_file(uploaded_file):
    suffix = ".pdf" if uploaded_file.name.endswith(".pdf") else os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name

def main():
    st.header("Step 3: Blood Report")
    
    # ADDED: Consistent patient info check
    if "form_data" not in st.session_state:
        st.warning("Please complete Step 1: Patient Info first")
        return

    with st.form("blood_report_form"):
        blood_file = st.file_uploader("Upload Blood Report (PDF/Image)", type=["pdf", "png", "jpg", "jpeg"], key="blood_file")
        submitted = st.form_submit_button("Submit Blood Report")
        if submitted:
            if blood_file:
                # save and extract
                path = save_uploaded_file(blood_file)
                blood_data = extract_report(path, report_type="blood")
                st.session_state["blood_data"] = blood_data
                st.success("Blood report processed!")
                logger.info(f"Blood report extracted: {blood_data['text'][:100]}...")
                # push to patient history vector DB
                pid = st.session_state["form_data"]["full_name"]
                add_to_health_history(pid, "blood", blood_data["text"], blood_data["tables"])
            else:
                st.error("Please upload a blood report file.")

if __name__ == "__main__":
    main()