import streamlit as st
from utils.logger import setup_logger
import re

logger = setup_logger("patient_info")

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("streamlit/assets/style.css")

def validate_height(height: str) -> float:
    """Validate and convert height input"""
    try:
        if "cm" in height:
            height_value = float(re.sub(r"[^\d.]", "", height))
            return height_value / 100
        elif "'" in height or '"' in height:
            parts = re.split(r"['\"]", height)
            feet = float(parts[0]) if parts[0] else 0
            inches = float(parts[1]) if len(parts) > 1 and parts[1] else 0
            return (feet * 12 + inches) * 0.0254
        else:
            return float(height)
    except ValueError:
        return None

def validate_weight(weight: str) -> float:
    """Validate and convert weight input"""
    try:
        if "kg" in weight:
            return float(re.sub(r"[^\d.]", "", weight))
        elif "lbs" in weight or "lb" in weight:
            lbs = float(re.sub(r"[^\d.]", "", weight))
            return lbs * 0.453592
        else:
            return float(weight)
    except ValueError:
        return None

def main():
    st.header("Step 1: Your Health Profile")
    st.info("Complete your health profile to get personalized recommendations")

    with st.form("health_profile_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Personal Information")
            full_name = st.text_input("Full Name", key="full_name")
            age = st.number_input("Age", min_value=1, max_value=120, value=30, key="age")
            gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"], key="gender_selectbox")
            phone = st.text_input("Phone Number", key="phone")
            email = st.text_input("Email", key="email")
            location = st.text_input("Location (City)", key="location")
            blood_group = st.selectbox("Blood Group", 
                                     ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"], 
                                     key="blood_group")
            
        with col2:
            st.subheader("Health Metrics")
            height = st.text_input("Height (e.g., 1.75m, 175cm, 5'9\")", key="height")
            weight = st.text_input("Weight (e.g., 75kg, 165lbs)", key="weight")
            
            activity_level = st.selectbox(
                "Activity Level",
                ["Sedentary (little/no exercise)", 
                 "Lightly Active (light exercise 1-3 days/week)",
                 "Moderately Active (moderate exercise 3-5 days/week)",
                 "Very Active (hard exercise 6-7 days/week)",
                 "Extra Active (very hard exercise & physical job)"],
                key="activity_level"
            )
            
            allergies = st.text_area("Allergies (if any)", key="allergies", height=80)
            blood_report_data = st.text_area(
                "Recent Blood Test Results", 
                key="blood_report_data", 
                height=100
            )
            
            st.subheader("Emergency Contact")
            emergency_contact_name = st.text_input("Emergency Contact Name", key="emergency_contact_name")
            emergency_contact_phone = st.text_input("Emergency Contact Phone", key="emergency_contact_phone")

        medical_history = st.text_area("Medical History", key="history", height=100)

        submitted = st.form_submit_button("Save Health Profile")
        if submitted:
            errors = []
            
            if not full_name:
                errors.append("Full name is required")
            if not location:
                errors.append("Location is required")
            if not emergency_contact_phone:
                errors.append("Emergency contact phone is required")
                
            height_value = validate_height(height) if height else None
            weight_value = validate_weight(weight) if weight else None
            
            if not height_value:
                errors.append("Please enter a valid height (e.g., 1.75m, 175cm, 5'9\")")
            if not weight_value:
                errors.append("Please enter a valid weight (e.g., 75kg, 165lbs)")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                form_data = {
                    "full_name": full_name,
                    "age": age,
                    "height": height_value,
                    "weight": weight_value,
                    "gender": gender,
                    "phone": phone,
                    "email": email,
                    "allergies": allergies,
                    "blood_report_data": blood_report_data,
                    "location": location,
                    "blood_group": blood_group,
                    "activity_level": activity_level,
                    "medical_history": medical_history,
                    "emergency_contact_name": emergency_contact_name or "Not provided",
                    "emergency_contact_phone": emergency_contact_phone
                }
                # CORRECTED SESSION STATE KEY
                st.session_state["form_data"] = form_data
                logger.info(f"Health profile submitted: {form_data}")
                st.success("Health profile saved! Proceed to Set Your Health Goal.")
                st.balloons()

if __name__ == "__main__":
    main()