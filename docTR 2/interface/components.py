import streamlit as st

def create_form_field(label, key, field_type="text"):
    """Create a reusable form field."""
    if field_type == "text":
        return st.text_input(label, key=key)
    elif field_type == "dropdown":
        return st.selectbox(label, options=[""], key=key)
    elif field_type == "textarea":
        return st.text_area(label, key=key)
    elif field_type == "file":
        return st.file_uploader(label, key=key)
    return None