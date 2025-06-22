import streamlit as st
from utils.logger import setup_logger
from prognosis.llm import process_health_data
from storage.chroma_db import get_health_history, add_to_health_history
from utils.pdf_report import create_pdf_report
from storage.appointment import get_doctors_for_booking, book_appointment
import re
import logging

logger = setup_logger("health_recommendation")

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("streamlit/assets/style.css")

def calculate_bmi(weight: float, height: float) -> float:
    return weight / (height ** 2) if height > 0 else 0

def get_weight_status(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    elif 18.5 <= bmi < 25:
        return "Normal weight"
    elif 25 <= bmi < 30:
        return "Overweight"
    else:
        return "Obese"

def parse_macro_breakdown(macro_text: str) -> dict:
    """Robust macro parsing with fallback to default values"""
    if not macro_text or not isinstance(macro_text, str):
        return {}
    
    # Try to parse with multiple patterns
    patterns = [
        # Pattern 1: "Protein: 150g (30% of calories)"
        r"Protein:? ([\d.]+)g?.*?\(([\d.]+)%",
        # Pattern 2: "Protein: 150g (30%)"
        r"Protein:? ([\d.]+)g?.*?\(([\d.]+)%\)",
        # Pattern 3: "Protein (g): 150 (30%)"
        r"Protein \(?g\)?:? ([\d.]+).*?\(([\d.]+)%",
        # Pattern 4: Just numbers near "Protein"
        r"Protein[^\d]*([\d.]+)[^\d]*([\d.]+)"
    ]
    
    macros = {}
    for pattern in patterns:
        try:
            match = re.search(pattern, macro_text, re.IGNORECASE)
            if match:
                macros["protein_grams"] = float(match.group(1))
                if match.lastindex > 1:
                    macros["protein_percent"] = float(match.group(2))
                break
        except Exception:
            pass
    
    # Set defaults for other macros if not found
    if "protein_grams" in macros:
        macros.setdefault("carbs_grams", macros["protein_grams"] * 1.5)
        macros.setdefault("fats_grams", macros["protein_grams"] * 0.7)
        macros.setdefault("carbs_percent", 50)
        macros.setdefault("fats_percent", 25)
    
    return macros

def display_meal_plan(meal_plan: str):
    """Display meal plan with robust handling for missing data"""
    if not meal_plan:
        st.warning("No meal plan available")
        return
    
    # Try to show whatever content we have
    st.subheader("Meal Plan")
    st.write(meal_plan)

def main():
    st.header("Step 5: Your Health & Nutrition Plan")
    st.info("Personalized recommendations based on your health profile and goals")
    
    required_keys = ["form_data", "symptoms_data", "goal"]
    missing_keys = [key for key in required_keys if key not in st.session_state]
    
    if missing_keys:
        st.warning(f"Please complete previous steps first. Missing: {', '.join(missing_keys)}")
        return
    
    form = st.session_state["form_data"]
    goal = st.session_state["goal"]
    patient_id = form.get("full_name", "unknown")
    
    height = form.get("height", 1.7)
    weight = form.get("weight", 70)
    bmi = calculate_bmi(weight, height)
    weight_status = get_weight_status(bmi)
    
    with st.expander("📊 Your Health Summary", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("BMI", f"{bmi:.1f}", weight_status)
        with col2:
            st.metric("Current Weight", f"{weight:.1f} kg")
        with col3:
            target = goal.get('target_weight')
            target_display = f"{target:.1f} kg" if target is not None else "Not specified"
            st.metric("Target Weight", target_display)
    
    if st.button("Generate Health Plan", type="primary"):
        with st.spinner("Creating your personalized health plan..."):
            patient_data = {
                "patient_id": patient_id,
                "profile": form,
                "goal": goal,
                "symptoms_data": st.session_state["symptoms_data"],
                "blood_data": st.session_state["blood_data"],
                "history_context": get_health_history(patient_id)
            }
            try:
                res = process_health_data(patient_data)
                st.session_state["health_recommendation"] = res
                
                # Log full response for debugging
                logger.info("Health recommendation response:")
                logger.info(f"Keys: {list(res.keys())}")
                for key, value in res.items():
                    logger.info(f"{key}: {str(value)[:200]}")
                
            except Exception as e:
                st.error(f"Failed to generate health plan: {str(e)}")
                logger.error(f"Error in process_health_data: {str(e)}")
                return

    if "health_recommendation" in st.session_state:
        res = st.session_state["health_recommendation"]
        
        st.subheader("Nutrition Plan")
        
        # Handle calorie target
        calorie_target = res.get('calorie_target', 'Unknown')
        if isinstance(calorie_target, (int, float)):
            st.markdown(f"**Daily Calorie Target:** {calorie_target} kcal")
        else:
            st.markdown(f"**Daily Calorie Target:** {calorie_target}")
        
        # Handle macro breakdown
        if "macro_breakdown" in res:
            macro_text = res["macro_breakdown"]
            macros = parse_macro_breakdown(str(macro_text))
            
            if macros:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Protein", 
                             f"{macros.get('protein_grams', 0):.0f}g", 
                             f"{macros.get('protein_percent', 0):.0f}%")
                with col2:
                    st.metric("Carbs", 
                             f"{macros.get('carbs_grams', 0):.0f}g", 
                             f"{macros.get('carbs_percent', 0):.0f}%")
                with col3:
                    st.metric("Fats", 
                             f"{macros.get('fats_grams', 0):.0f}g", 
                             f"{macros.get('fats_percent', 0):.0f}%")
            else:
                st.warning("Could not parse macro breakdown")
                st.text_area("Raw Macro Breakdown", str(macro_text), height=100)
        else:
            st.warning("No macro breakdown available")
        
        # Handle nutrition guidance
        st.markdown("**Nutrition Guidance:**")
        nutrition_guidance = res.get('nutrition_guidance', '')
        if nutrition_guidance:
            st.write(nutrition_guidance)
        else:
            st.warning("No nutrition guidance available. Here are some general tips:")
            st.write("Focus on whole foods, stay hydrated, and ensure balanced meals with protein, carbs, and healthy fats.")
        
        # Handle meal plan
        st.subheader("Meal Plan")
        meal_plan = res.get("meal_plan", "")
        if meal_plan:
            display_meal_plan(meal_plan)
        else:
            st.warning("No meal plan available. Consider consulting a nutritionist for personalized meal planning.")
        
        # Handle grocery list
        st.subheader("Grocery List")
        grocery_list = res.get('grocery_list', '')
        if grocery_list:
            # If it's a list, convert to string
            if isinstance(grocery_list, list):
                grocery_list = "\n".join([f"- {item}" for item in grocery_list])
            
            # If it has markdown-like structure, render as markdown
            if any(char in grocery_list for char in ['-', '*', '•']):
                st.markdown(grocery_list)
            else:
                # Convert to bullet points
                items = [item.strip() for item in grocery_list.split('\n') if item.strip()]
                if items:
                    st.markdown("\n".join([f"- {item}" for item in items]))
                else:
                    st.info("No grocery items listed")
        else:
            st.info("No grocery list available")
        
        if st.button("🛒 Order Groceries via DoorDash", type="primary"):
            st.session_state["order_redirect"] = True
            st.success("Redirecting to DoorDash...")
        
        st.divider()
        
        if res.get('needs_doctor', False):
            st.warning("Based on your health profile, we recommend consulting a healthcare professional")
            location = form.get('location', 'unknown')
            condition = "general health"
            doctors = get_doctors_for_booking(condition, location)
            
            if doctors:
                st.subheader("Recommended Healthcare Professionals")
                for i, doctor in enumerate(doctors):
                    with st.expander(f"👨‍⚕️ {doctor['name']} ({doctor['specialty']})"):
                        st.write(f"**Location:** {doctor['location']}")
                        st.write(f"**Contact:** {doctor['phone']}")
                
                selected_index = st.selectbox(
                    "Select a doctor:",
                    options=range(len(doctors)),
                    format_func=lambda x: doctors[x]["name"],
                    key="doctor_select"
                )
                
                if st.button("Book Appointment", key="book_appointment"):
                    selected_doctor = doctors[selected_index]
                    booking_response = book_appointment(selected_doctor, {
                        "form_data": form,
                        "goal": goal
                    })
                    st.success("✅ Appointment booked successfully!")
                    st.write(booking_response)
                    st.session_state["booking_info"] = {
                        "doctor": selected_doctor,
                        "response": booking_response
                    }
            else:
                st.warning(f"No doctors available in {location}. Please consult a healthcare provider.")

        if st.button("📥 Download Full Plan", type="secondary"):
            try:
                pdf_path = create_pdf_report({
                    "form_data": form,
                    "goal": goal,
                    "recommendation": res
                }, res)
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "Download PDF Report",
                        data=f,
                        file_name="health_recommendation.pdf",
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"Failed to generate PDF: {str(e)}")
                logger.error(f"PDF generation error: {str(e)}")

        if st.button("💾 Save to Health History", type="secondary"):
            try:
                # Safely handle None values in nutrition_guidance
                nutrition_guidance = res.get('nutrition_guidance', '') or ''
                recommendation_text = (
                    f"BMI: {bmi:.1f}\n"
                    f"Calorie Target: {res.get('calorie_target', 'Unknown')}\n"
                    f"Nutrition Guidance: {nutrition_guidance[:100] + '...' if nutrition_guidance else 'N/A'}\n"
                )
                add_to_health_history(
                    user_id=patient_id,
                    report_type="Health Recommendation",
                    text=recommendation_text
                )
                st.success("Recommendation saved to health history!")
            except Exception as e:
                st.error(f"Failed to save to health history: {str(e)}")
                logger.error(f"Health history save error: {str(e)}")
        
        st.divider()
        st.info("**Disclaimer**: This health recommendation is AI-generated and should be verified by a professional.")

if __name__ == "__main__":
    # Enable detailed logging for debugging
    logging.basicConfig(level=logging.INFO)
    main()