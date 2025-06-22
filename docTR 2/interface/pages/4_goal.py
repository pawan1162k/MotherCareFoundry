import streamlit as st
from utils.logger import setup_logger
import re

logger = setup_logger("goal")

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("streamlit/assets/style.css")

def parse_goal(goal_text: str) -> dict:
    """Parse natural language goal into structured data"""
    goal_text = goal_text.lower().strip()
    
    # Initialize default values
    goal_type = "maintain"
    target_weight = None
    timeline = None
    
    # Detect goal type
    if "lose" in goal_text or "reduce" in goal_text or "shed" in goal_text:
        goal_type = "lose"
    elif "gain" in goal_text or "build" in goal_text or "increase" in goal_text:
        goal_type = "gain"
    elif "maintain" in goal_text or "keep" in goal_text:
        goal_type = "maintain"
    
    # Extract target weight
    weight_match = re.search(r'(\d+)\s*(kgs?|kilograms?|pounds?|lbs?)', goal_text)
    if weight_match:
        target_weight = float(weight_match.group(1))
        unit = weight_match.group(2).lower()
        if unit.startswith("lb") or unit.startswith("pound"):
            target_weight *= 0.453592  # Convert to kg
    
    # Extract timeline
    timeline_match = re.search(r'in (\d+)\s*(weeks?|months?|years?)', goal_text)
    if timeline_match:
        timeline = {
            "value": int(timeline_match.group(1)),
            "unit": timeline_match.group(2).rstrip('s')
        }
    
    return {
        "type": goal_type,
        "target_weight": target_weight,
        "timeline": timeline,
        "raw_text": goal_text
    }

def main():
    st.header("Step 4: Set Your Health Goal")
    st.info("Define your health and fitness objectives for personalized recommendations")
    
    # FIXED: Use consistent key
    if "form_data" not in st.session_state:
        st.warning("Please complete Step 1: Patient Info first")
        return
    
    profile = st.session_state["form_data"]  # FIXED: Use consistent key
    current_weight = profile["weight"]
    
    with st.expander("💡 Goal Examples"):
        st.write("""
        - "I want to lose 5kg in 2 months"
        - "Gain muscle mass to reach 80kg"
        - "Maintain my current weight while building muscle"
        - "Reduce body fat by 5% in 3 months"
        - "Get healthier without focusing on weight"
        """)
    
    with st.form("goal_form"):
        goal = st.text_area(
            "Describe your health goal in your own words", 
            key="goal_input", 
            height=120,
            placeholder="e.g., I want to lose 5kg in 2 months while building muscle"
        )
        
        # Auto-detect goal parameters
        if goal:
            parsed_goal = parse_goal(goal)
            goal_type = parsed_goal["type"].capitalize()
            target_weight = parsed_goal["target_weight"]
            timeline = parsed_goal["timeline"]
            
            if target_weight:
                st.info(f"Detected goal: {goal_type} weight to {target_weight:.1f}kg")
            else:
                st.info(f"Detected goal: {goal_type} weight")
        
        submitted = st.form_submit_button("Save Goal")
        if submitted:
            if not goal:
                st.error("Please describe your health goal")
                return
            
            # Store parsed goal
            goal_data = parse_goal(goal)
            goal_data["description"] = goal
            
            # Calculate weight difference if possible
            if current_weight and goal_data["target_weight"]:
                goal_data["weight_difference"] = abs(current_weight - goal_data["target_weight"])
            
            # FIXED: Use consistent key
            st.session_state["goal"] = goal_data
            logger.info(f"Health goal submitted: {goal_data}")
            st.success("Goal saved! Proceed to Health Recommendations.")
            st.balloons()

if __name__ == "__main__":
    main()