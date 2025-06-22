import streamlit as st
from utils.logger import setup_logger

logger = setup_logger("symptoms")

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("streamlit/assets/style.css")

def main():
    st.header("Step 2: Symptoms")
    
    # ADDED: Consistent patient info check
    if "form_data" not in st.session_state:
        st.warning("Please complete Step 1: Patient Info first")
        return

    common_symptoms = ["Fever", "Cough", "Shortness of Breath", "Fatigue", "Headache", "Nausea", "Chest Pain"]
    selected_symptoms = []
    severity = {}

    with st.form("symptoms_form"):
        st.markdown("### Select Common Symptoms and Rate Severity:")

        for symptom in common_symptoms:
            col1, col2 = st.columns([1, 3])
            with col1:
                checked = st.checkbox(symptom, key=f"check_{symptom}")
            with col2:
                slider_val = st.slider(
                    f"Severity for {symptom}",
                    1, 5,
                    key=f"slider_{symptom}",
                    # disabled=not checked
                )
                if checked:
                    selected_symptoms.append(symptom)
                    severity[symptom] = slider_val

        custom_symptoms = st.text_area("Add any other symptoms not listed above:", key="custom_symptoms")

        submitted = st.form_submit_button("Submit Symptoms")
        if submitted:
            all_symptoms = {
                "selected": selected_symptoms,
                "custom": custom_symptoms,
                "severity": severity
            }
            st.session_state["symptoms_data"] = all_symptoms
            logger.info(f"Symptoms submitted: {all_symptoms}")
            st.success("Symptoms submitted! Proceed to Blood Report.")

if __name__ == "__main__":
    main()