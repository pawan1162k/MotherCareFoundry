from langgraph.graph import StateGraph, END
from typing import Dict, Any, Literal, TypedDict
from utils.logger import setup_logger
from prognosis.llm import process_workout_data, process_health_data

logger = setup_logger("workflow")

class FitnessState(TypedDict):
    action: str  # The action to perform (e.g., "workout_generation")
    user_data: Dict[str, Any]  # User profile and preferences
    health_goals: Dict[str, Any]  # Current health goals
    fitness_status: Dict[str, Any]  # Current fitness status
    history_context: str  # Context from health history
    workflow_output: Dict[str, Any]  # Output of the workflow
    next_node: Literal["generate_response", "END"]  # Next node in the workflow

def action_router(state: FitnessState) -> Dict[str, Any]:
    """Route to the appropriate action handler"""
    action = state.get("action")
    logger.info(f"Routing action: {action}")
    
    # All actions go directly to generate_response in this simplified version
    return {"next_node": "generate_response"}

def generate_response(state: FitnessState) -> Dict[str, Any]:
    """Generate the appropriate response based on the action"""
    action = state["action"]
    user_data = state["user_data"]
    goals = state["health_goals"]
    status = state["fitness_status"]
    context = state["history_context"]
    
    try:
        if action == "workout_generation":
            workout_data = {
                "profile": user_data,
                "goal": goals,
                "health_recommendation": status,
                "workout_type": "Custom",
                "intensity": status.get("intensity", 3)
            }
            plan = process_workout_data(workout_data)
            response = {
                "action": "workout_generation",
                "details": "Here's your personalized workout plan:",
                "plan": plan
            }
            
        elif action == "meal_plan":
            health_data = {
                "patient_id": user_data.get("full_name", "user"),
                "profile": user_data,
                "goal": goals,
                "history_context": context
            }
            res = process_health_data(health_data, goals)
            response = {
                "action": "meal_plan",
                "details": "Here's your personalized meal plan:",
                "plan": res
            }
            
        elif action == "goal_adjustment":
            # Simple goal adjustment logic
            response = {
                "action": "goal_adjustment",
                "details": "Your goals have been updated successfully!",
                "new_goals": goals
            }
            
        elif action == "progress_report":
            # Generate progress report
            progress = f"""
            Fitness Progress Report:
            - Goal: {goals.get('description', 'No goal set')}
            - Last Workout: {status.get('last_workout', 'Not recorded')}
            - Nutrition Status: {status.get('nutrition', 'Balanced')}
            - Recovery Score: {status.get('recovery_score', 7)}/10
            """
            response = {
                "action": "progress_report",
                "details": progress
            }
            
        elif action == "nutrition_tips":
            # Provide nutrition tips
            tips = "Focus on protein-rich foods after workouts, stay hydrated, and include colorful vegetables in every meal."
            response = {
                "action": "nutrition_tips",
                "details": tips
            }
            
        elif action == "recovery_advice":
            # Provide recovery advice
            advice = "Ensure you're getting 7-9 hours of sleep, consider foam rolling, and stay hydrated."
            response = {
                "action": "recovery_advice",
                "details": advice
            }
            
        else:
            response = {
                "action": "error",
                "details": f"Unknown action: {action}"
            }
            
        return {
            "workflow_output": response,
            "next_node": "END"
        }
        
    except Exception as e:
        logger.error(f"Action processing error: {e}")
        return {
            "workflow_output": {
                "action": "error",
                "details": f"Failed to process action: {str(e)}"
            },
            "next_node": "END"
        }

# Build the state graph
workflow = StateGraph(FitnessState)
workflow.add_node("action_router", action_router)
workflow.add_node("generate_response", generate_response)

# Set entry point
workflow.set_entry_point("action_router")

# Add edges
workflow.add_edge("action_router", "generate_response")
workflow.add_edge("generate_response", END)

# Compile the graph
app = workflow.compile()

def run_workflow(user_context: Dict[str, Any], action: str) -> Dict[str, Any]:
    logger.info(f"Starting fitness workflow for action: {action}")
    
    # Create initial state
    state = {
        "action": action,
        "user_data": user_context["user_data"],
        "health_goals": user_context["health_goals"],
        "fitness_status": user_context["fitness_status"],
        "history_context": user_context["history_context"],
        "workflow_output": None,
        "next_node": None
    }
    
    try:
        result_state = app.invoke(state)
        logger.info(f"Workflow completed: {result_state.get('workflow_output')}")
        return result_state.get("workflow_output", {})
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        return {"action": "error", "details": str(e)}