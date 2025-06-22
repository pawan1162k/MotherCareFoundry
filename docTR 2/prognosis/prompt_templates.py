from utils.logger import setup_logger

logger = setup_logger("prompt_templates")
# Updated health prompt template
def get_health_prompt(health_data):
    profile = health_data["profile"]
    goal = health_data["goal"]
    
    prompt = f"""
You are a health advisor with expertise in nutrition and fitness. Your task is to create a comprehensive health and nutrition plan based on the user's profile and goals.

**Response MUST follow this exact format:**

**BMI**: [Calculated BMI value]
**Weight Status**: [Underweight/Normal/Overweight/Obese]
**Daily Calorie Target**: [X] kcal
**Macro Breakdown**: 
Protein: [X]g ([Y]% of calories)
Carbs: [X]g ([Y]% of calories)
Fats: [X]g ([Y]% of calories)

**Nutrition Guidance**:
[2-3 paragraph explanation of dietary approach]

**3-Day Meal Plan**:
Day 1:
- Breakfast: [Meal description] ([Calories] kcal)
- Lunch: [Meal description] ([Calories] kcal)
- Dinner: [Meal description] ([Calories] kcal)
- Snacks: [Snack description] ([Calories] kcal)

Day 2:
- Breakfast: [Meal description] ([Calories] kcal)
- Lunch: [Meal description] ([Calories] kcal)
- Dinner: [Meal description] ([Calories] kcal)
- Snacks: [Snack description] ([Calories] kcal)

Day 3:
- Breakfast: [Meal description] ([Calories] kcal)
- Lunch: [Meal description] ([Calories] kcal)
- Dinner: [Meal description] ([Calories] kcal)
- Snacks: [Snack description] ([Calories] kcal)

**Grocery List**:
- [Category]:
  - [Item 1]
  - [Item 2]
- [Another Category]:
  - [Item 3]
  - [Item 4]

**Needs Doctor**: [Yes/No] - [Brief reason if yes]

**User Profile**:
- Age: {profile['age']}
- Gender: {profile['gender']}
- Height: {profile['height']} m
- Weight: {profile['weight']} kg
- Activity Level: {profile['activity_level']}
- Allergies: {profile.get('allergies', 'None')}
- Medical History: {profile.get('medical_history', 'None')}
- Blood Report: {profile.get('blood_report_data', 'No recent blood work')}

**Health Goal**:
{goal['description']} (Goal Type: {goal.get('type', 'Custom')})
"""
    logger.info(f"Health prompt generated (first 200 chars): {prompt[:200]}...")
    return prompt

# In prognosis/prompt_templates.py

def get_workout_prompt(workout_data):
    profile = workout_data["profile"]
    goal = workout_data["goal"]
    health_rec = workout_data.get("health_recommendation", {})
    
    prompt = f"""
You are a fitness advisor creating a personalized 3-day workout plan based on the user's profile, goals, and health recommendations.

**Response MUST follow this exact format:**

**Calorie Burn Target**: [X] kcal/day

**Plan Overview**:
[2-3 paragraph explanation of the workout philosophy]

**Schedule**:
Day 1: [Focus Area]
- Duration: [X] minutes
- Warm-up: [Description] (5 min)
- Exercises:
  1. [Exercise 1]: [Sets]x[Reps] or [Duration]
  2. [Exercise 2]: [Sets]x[Reps] or [Duration]
  3. [Exercise 3]: [Sets]x[Reps] or [Duration]
  4. [Exercise 4]: [Sets]x[Reps] or [Duration]
- Cool-down: [Description] (5 min)
- Estimated Calorie Burn: [X] kcal

Day 2: [Focus Area]
[Same structure]

Day 3: [Focus Area]
[Same structure]

**Explanation**:
[Summary of how the plan progresses and safety considerations]

**User Profile**:
- Age: {profile['age']}
- Gender: {profile['gender']}
- Height: {profile['height']} m
- Weight: {profile['weight']} kg
- Activity Level: {profile['activity_level']}
- Medical History: {profile.get('medical_history', 'None')}

**Health Goal**:
{goal['description']}

**Health Recommendations**:
- Calorie Target: {health_rec.get('calorie_target', 'Unknown')} kcal
- Weight Status: {health_rec.get('weight_status', 'Unknown')}
- Health Status: {health_rec.get('health_status', 'Unknown')}
"""
    logger.info(f"Workout prompt generated (first 200 chars): {prompt[:200]}...")
    return prompt