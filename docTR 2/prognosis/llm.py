import re
from huggingface_hub import InferenceClient
from utils.config import HUGGINGFACE_TOKEN, OPENBIOLLM_MODEL
from utils.logger import setup_logger
from prognosis.prompt_templates import get_health_prompt, get_workout_prompt

logger = setup_logger("llm")

def init_llm():
    """Initialize Hugging Face InferenceClient for OpenBioLLM."""
    try:
        client = InferenceClient(
            model=OPENBIOLLM_MODEL,
            token=HUGGINGFACE_TOKEN,
            provider="nebius"
        )
        logger.info(f"LLM client initialized: {OPENBIOLLM_MODEL}")
        return client
    except Exception as e:
        logger.error(f"LLM initialization error: {e}")
        return None

def parse_health_response(text: str) -> dict:
    """
    Parse LLM response for health recommendations, handling Markdown and flexible formatting.
    """
    # Normalize the text for easier parsing
    text = re.sub(r'\*\*', '', text)  # Remove bold markers
    text = re.sub(r'\s+', ' ', text)  # Collapse multiple spaces
    
    # Extract key sections using more robust parsing
    sections = {
        "bmi": r"BMI:\s*([\d.]+)",
        "weight_status": r"Weight Status:\s*([\w\s]+)",
        "calorie_target": r"Daily Calorie Target:\s*([\d,]+)\s*kcal",
        "macro_breakdown": r"Macro Breakdown:\s*([\s\S]+?)(?=Nutrition Guidance:|$)",
        "nutrition_guidance": r"Nutrition Guidance:\s*([\s\S]+?)(?=3-Day Meal Plan:|$)",
        "meal_plan": r"3-Day Meal Plan:\s*([\s\S]+?)(?=Grocery List:|$)",
        "grocery_list": r"Grocery List:\s*([\s\S]+?)(?=Needs Doctor:|$)",
        "needs_doctor": r"Needs Doctor:\s*(yes|no|true|false)"
    }
    
    parsed = {}
    for key, pattern in sections.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed[key] = match.group(1).strip()
        else:
            # Try more flexible matching without section headers
            fallback = re.search(pattern.replace(r"\s*", r"\s*"), text, re.IGNORECASE)
            parsed[key] = fallback.group(1).strip() if fallback else None
    
    # Process special cases
    try:
        parsed["bmi"] = float(parsed["bmi"]) if parsed["bmi"] else 0.0
    except (ValueError, TypeError):
        parsed["bmi"] = 0.0
        
    # Process needs_doctor field
    if parsed["needs_doctor"]:
        parsed["needs_doctor"] = parsed["needs_doctor"].lower() in ["yes", "true"]
    else:
        parsed["needs_doctor"] = False
    
    # Validate weight status
    valid_weight_statuses = {"Underweight", "Normal weight", "Overweight", "Obese"}
    if parsed["weight_status"] and parsed["weight_status"] not in valid_weight_statuses:
        logger.warning(f"Invalid weight status '{parsed['weight_status']}', setting to Unknown")
        parsed["weight_status"] = "Unknown"

    logger.info(f"Parsed health response: BMI={parsed['bmi']}, Calories={parsed['calorie_target']}")
    return parsed

def parse_workout_response(text: str) -> dict:
    """
    Parse LLM response for workout plan, handling Markdown and flexible formatting.
    """
    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r'\*\*', '', text)

    # Extract key sections with improved patterns
    sections = {
        "calorie_burn_target": r"calorie burn target[:\s]*([\d,]+)\s*kcal",
        "overview": r"overview[:\s]*([\s\S]+?)(?=\n\s*Schedule:|$)",
        "schedule": r"schedule[:\s]*([\s\S]+?)(?=\n\s*Explanation:|$)",
        "explanation": r"explanation[:\s]*([\s\S]+)"
    }
    
    parsed = {}
    for key, pattern in sections.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        parsed[key] = match.group(1).strip() if match else None
    
    # Parse schedule into days
    if parsed["schedule"]:
        days = []
        day_pattern = r"Day \d+:(.+?)(?=(Day \d+:|$))"
        day_matches = re.finditer(day_pattern, parsed["schedule"], re.IGNORECASE | re.DOTALL)
        
        for match in day_matches:
            day_text = match.group(1).strip()
            day_data = {
                "focus": re.search(r"Focus[:\s]*(.+)", day_text).group(1).strip() if re.search(r"Focus", day_text) else "General Fitness",
                "duration": re.search(r"Duration[:\s]*(.+)", day_text).group(1).strip() if re.search(r"Duration", day_text) else "30-45 minutes",
                "calorie_burn": re.search(r"Calorie Burn[:\s]*([\d,]+)\s*kcal", day_text).group(1).strip() if re.search(r"Calorie Burn", day_text) else "Unknown",
                "details": day_text
            }
            days.append(day_data)
        
        parsed["schedule"] = days
    else:
        parsed["schedule"] = []

    logger.info(f"Parsed workout response: Days={len(parsed['schedule'])}")
    return parsed
def process_health_data(health_data: dict, client=None) -> dict:
    """
    Generate health recommendations using OpenBioLLM based on health profile and goal.
    """
    if client is None:
        client = init_llm()
    if client is None:
        logger.warning("No LLM client available.")
        return {
            "bmi": 0.0,
            "weight_status": "Unknown",
            "calorie_target": "Unknown",
            "macro_breakdown": "Unknown",
            "nutrition_guidance": "LLM init failed",
            "meal_plan": [],
            "grocery_list": "No grocery list provided",
            "needs_doctor": False
        }

    prompt = get_health_prompt(health_data)
    messages = [
        {"role": "system", "content": "You are a health advisor with expertise in nutrition and fitness."},
        {"role": "user", "content": prompt}
    ]

    try:
        completion = client.chat.completions.create(
            model=OPENBIOLLM_MODEL,
            messages=messages,
            max_tokens=1500  # Increased for detailed meal plans
        )
        text = completion.choices[0].message.content.strip()
        logger.info(f"Health response:\n{text[:500]}...")
        return parse_health_response(text)

    except Exception as e:
        logger.error(f"Health recommendation generation error: {e}")
        return {
            "bmi": 0.0,
            "weight_status": "Unknown",
            "calorie_target": "Unknown",
            "macro_breakdown": "Unknown",
            "nutrition_guidance": str(e),
            "meal_plan": [],
            "grocery_list": "No grocery list provided",
            "needs_doctor": False
        }

def process_workout_data(workout_data: dict, client=None) -> dict:
    """
    Generate a workout plan using OpenBioLLM based on health profile, goal, and recommendations.
    """
    if client is None:
        client = init_llm()
    if client is None:
        logger.warning("No LLM client available.")
        return {
            "calorie_burn_target": "Unknown",
            "overview": "No workout plan provided",
            "schedule": [],
            "explanation": "LLM init failed."
        }

    prompt = get_workout_prompt(workout_data)
    messages = [
        {"role": "system", "content": "You are a fitness advisor with expertise in creating workout plans."},
        {"role": "user", "content": prompt}
    ]

    try:
        completion = client.chat.completions.create(
            model=OPENBIOLLM_MODEL,
            messages=messages,
            max_tokens=1200  # Increased for detailed schedules
        )
        text = completion.choices[0].message.content.strip()
        logger.info(f"Workout response:\n{text[:500]}...")
        return parse_workout_response(text)

    except Exception as e:
        logger.error(f"Workout plan generation error: {e}")
        return {
            "calorie_burn_target": "Unknown",
            "overview": "No workout plan provided",
            "schedule": [],
            "explanation": str(e)
        }

def generate_chat_response(user_query: str, health_context: dict, client=None) -> str:
    """
    Generate a response to a user's health-related question.
    """
    if client is None:
        client = init_llm()
    if client is None:
        logger.warning("No LLM client available.")
        return "Sorry, I couldn't process your question due to a technical issue."
    
    # Build context string
    context_str = (
        f"Health Profile:\n"
        f"- Age: {health_context['profile']['age']}\n"
        f"- Gender: {health_context['profile']['gender']}\n"
        f"- Height: {health_context['profile']['height']} m\n"
        f"- Weight: {health_context['profile']['weight']} kg\n"
        f"- Activity Level: {health_context['profile']['activity_level']}\n\n"
        
        f"Health Goal:\n"
        f"{health_context['goal']['description']}\n\n"
        
        f"Current Recommendations:\n"
        f"- Calorie Target: {health_context.get('recommendation', {}).get('calorie_target', 'Unknown')} kcal\n"
        f"- Nutrition Guidance: {health_context.get('recommendation', {}).get('nutrition_guidance', '')[:100]}...\n"
    )
    
    prompt = f"""
You are a health advisor with expertise in nutrition and fitness. Answer the user's question based on their health profile, goals, and current recommendations. Provide accurate, personalized advice in a friendly, conversational tone.

**Health Context**:
{context_str}

**User Question**:
{user_query}

**Response Guidelines**:
1. Be specific to the user's profile and goals
2. Keep responses concise but informative
3. Offer practical, actionable advice
4. Avoid medical disclaimers unless necessary
5. Use bullet points for complex information

**Response**:
"""
    messages = [
        {"role": "system", "content": "You are a health advisor with expertise in nutrition and fitness."},
        {"role": "user", "content": prompt}
    ]
    try:
        completion = client.chat.completions.create(
            model=OPENBIOLLM_MODEL,
            messages=messages,
            max_tokens=512
        )
        response = completion.choices[0].message.content.strip()
        logger.info(f"Chat response:\n{response[:300]}...")
        return response
    except Exception as e:
        logger.error(f"Chat response generation error: {e}")
        return "Sorry, I couldn't process your question. Please try again later."