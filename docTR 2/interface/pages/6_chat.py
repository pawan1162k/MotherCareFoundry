import streamlit as st
from utils.logger import setup_logger
from storage.chroma_db import get_health_history
from prognosis.llm import generate_chat_response
from workflows.workflow import run_workflow
import re
import logging

logger = setup_logger("chat")

def build_history_context(user_id: str, n_results: int = 10) -> str:
    """Build context from fitness/diet history instead of medical reports"""
    logger.info(f"Building history context for user_id: {user_id}")
    try:
        recs = get_health_history(user_id, n_results=n_results)
        if not recs:
            logger.info("No health records found.")
            return "No previous health records found."
        
        ctx = "Recent Health History:\n"
        for r in recs:
            # Use 'report_type' instead of 'record_type'
            report_type = r["metadata"].get("report_type", "ENTRY").title()
            timestamp = r["metadata"].get("timestamp", "")
            content = r["document"].strip()
            
            ctx += f"---\n[{report_type} - {timestamp}]\n{content}\n"
        
        logger.info(f"History context built: {ctx[:100]}...")
        return ctx
    except Exception as e:
        logger.error(f"Error in build_history_context: {e}")
        return f"Error retrieving history: {str(e)}"

def simplify_fitness_terms(response: str) -> str:
    """Simplify fitness/nutrition jargon in responses"""
    # Remove redundant phrases
    response = re.sub(
        r"Based on (your|the) (fitness data|nutrition log|workout history)[,\.\s]*", 
        "", 
        response, 
        flags=re.IGNORECASE
    )
    
    # Simplify fitness terminology
    replacements = {
        r"macronutrients": "nutrients",
        r"cardiovascular exercise": "cardio",
        r"resistance training": "strength training",
        r"caloric deficit": "eating fewer calories",
        r"hypertrophy": "muscle growth",
        r"aerobic capacity": "stamina",
        r"macros": "protein/fat/carbs",
        r"micronutrients": "vitamins/minerals",
        r"thermic effect of food": "calories burned digesting",
        r"progressive overload": "gradually increasing difficulty",
        r"body composition": "muscle/fat ratio"
    }
    
    for pattern, replacement in replacements.items():
        response = re.sub(pattern, replacement, response, flags=re.IGNORECASE)
    
    return response

def format_response(response: str) -> str:
    """Format responses for better readability with fitness focus"""
    # Remove redundant labels
    response = response.replace("Answer:", "").replace("Response:", "").strip()
    
    # Add emojis for common fitness concepts
    emoji_map = {
        "protein": "🥩",
        "cardio": "🏃‍♂️",
        "strength": "💪",
        "nutrition": "🍎",
        "recovery": "😴",
        "progress": "📈",
        "water": "💧",
        "calories": "🔥"
    }
    
    for term, emoji in emoji_map.items():
        response = response.replace(term, f"{term}{emoji}")
    
    # Add line breaks before key points
    response = re.sub(r'(\d+\.|\-) ', r'\n\1 ', response)
    
    return response

def main():
    logger.info("Starting health chat")
    st.header("Health & Fitness Assistant")
    st.write("Ask questions about your workouts, nutrition, or health progress like:")
    st.caption("• 'How did I sleep last week?'\n• 'Suggest a post-workout meal'\n• 'Compare my running progress'")
    
    # Initialize chat history if not exists
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    
    # Check for required session state keys
    if "form_data" not in st.session_state:
        st.warning("Please complete the initial health assessment first")
        return

    try:
        user_data = st.session_state["form_data"]
        user_id = user_data.get("full_name", "default_user")
        
        # Initialize health goals if not exists
        if "goal" not in st.session_state:
            st.session_state["goal"] = {"description": "Maintain fitness"}
            
        health_goals = st.session_state["goal"]
        
        # Initialize fitness status with safe defaults
        fitness_status = {
            "last_workout": st.session_state.get("workout_plan", {}).get("last_completed", "Not recorded"),
            "nutrition": st.session_state.get("diet_status", "Balanced"),
            "recovery_score": st.session_state.get("recovery_score", 7),
            "goal_progress": health_goals.get("progress", 0)
        }
        
        status_context = f"""
        Current Fitness Status:
        - Last workout: {fitness_status['last_workout']}
        - Nutrition: {fitness_status['nutrition']}
        - Recovery: {fitness_status['recovery_score']}/10
        - Weekly goal progress: {fitness_status['goal_progress']}%
        """
        
        logger.info(f"User ID: {user_id}, Goals: {health_goals.get('description')}")
    except Exception as e:
        logger.error(f"Error accessing session state: {e}")
        st.error(f"Error loading your health data: {str(e)}")
        return

    # Display chat history
    for message in st.session_state["chat_history"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about your health or fitness..."):
        logger.info(f"User query: {prompt}")
        prompt_lower = prompt.lower().strip()

        # Handle greetings
        if prompt_lower in ["hi", "hello", "hey"]:
            response = f"Hello {user_data.get('first_name', 'there')}! Ready to crush your health goals today? 💪"
            st.session_state["chat_history"].append({"role": "user", "content": prompt})
            st.session_state["chat_history"].append({"role": "assistant", "content": response})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                st.markdown(response)
            return
        
        # Handle thanks
        elif any(phrase in prompt_lower for phrase in ["thank you", "thanks", "appreciate it"]):
            response = "You're welcome! Keep up the great work 🙌"
            st.session_state["chat_history"].append({"role": "user", "content": prompt})
            st.session_state["chat_history"].append({"role": "assistant", "content": response})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                st.markdown(response)
            return

        # Handle fitness action triggers
        fitness_triggers = {
            "create a workout": "workout_generation",
            "generate meal plan": "meal_plan",
            "adjust my goal": "goal_adjustment",
            "show progress": "progress_report",
            "nutrition advice": "nutrition_tips",
            "recovery tip": "recovery_advice",
            "track my sleep": "sleep_tracking",
            "log my workout": "workout_logging"
        }
        
        triggered_action = None
        for trigger, action in fitness_triggers.items():
            if trigger in prompt_lower:
                triggered_action = action
                break
        
        if triggered_action:
            user_context = {
                "user_id": user_id,
                "user_data": user_data,
                "health_goals": health_goals,
                "fitness_status": fitness_status,
                "history_context": build_history_context(user_id)
            }
            
            logger.info(f"Running fitness workflow: {triggered_action}")
            
            try:
                workflow_result = run_workflow(user_context, triggered_action)
                
                if workflow_result.get('status') == 'error':
                    response = f"⚠️ {workflow_result.get('message', 'Could not complete your request')}"
                else:
                    response = format_response(workflow_result.get('response', 'Action completed!'))
                
                st.session_state["chat_history"].append({"role": "user", "content": prompt})
                st.session_state["chat_history"].append({"role": "assistant", "content": response})
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    st.markdown(response)
                return
                
            except Exception as e:
                logger.error(f"Workflow error: {e}")
                response = "🚧 Our fitness engine is busy. Try again in a minute!"
                st.session_state["chat_history"].append({"role": "user", "content": prompt})
                st.session_state["chat_history"].append({"role": "assistant", "content": response})
                with st.chat_message("assistant"):
                    st.markdown(response)
                return

        # Handle all other health/fitness queries
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            context = build_history_context(user_id)
            full_context = f"{context}\n\n{status_context}"
            
            # Create proper health context dictionary
            health_context = {
                "profile": user_data,
                "goal": health_goals,
                "fitness_status": fitness_status,
                "history_context": context
            }
        except Exception as e:
            logger.error(f"Context error: {e}")
            st.error(f"Error loading your health history: {str(e)}")
            return

        with st.spinner("Analyzing your health data..."):
            try:
                # Generate response with fitness focus
                raw_response = generate_chat_response(
                    user_query=prompt,
                    health_context=health_context
                )
                
                # Simplify fitness terminology
                response = simplify_fitness_terms(raw_response)
                
                # Format for readability
                response = format_response(response)
                
                st.session_state["chat_history"].append({"role": "assistant", "content": response})
                with st.chat_message("assistant"):
                    st.markdown(response)
                logger.info(f"Response generated: {response[:100]}...")
            except Exception as e:
                logger.error(f"Response error: {e}")
                response = "❌ Couldn't process that. Try asking about workouts, nutrition, or health metrics!"
                st.session_state["chat_history"].append({"role": "assistant", "content": response})
                with st.chat_message("assistant"):
                    st.markdown(response)

if __name__ == "__main__":
    main()