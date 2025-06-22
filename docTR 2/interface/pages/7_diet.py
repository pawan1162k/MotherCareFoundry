import streamlit as st
import os
import base64
import time
from io import BytesIO
from PIL import Image
import google.generativeai as genai
from googleapiclient.discovery import build
from utils.logger import setup_logger
from storage.chroma_db import add_to_health_history
import re

logger = setup_logger("diet")

# Initialize Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY not found in environment variables")
    st.error("Google API key missing. Please contact support.")
    st.stop()
genai.configure(api_key=GOOGLE_API_KEY)
MODEL_NAME = "gemini-1.5-flash"  # Higher free tier quotas
logger.info(f"Gemini API initialized with model: {MODEL_NAME}")

# Initialize YouTube API
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    logger.error("YOUTUBE_API_KEY not found in environment variables")
    st.error("YouTube API key missing. Please contact support.")
    st.stop()
youtube_service = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
logger.info("YouTube API initialized")

def identify_ingredients_from_image(image: Image.Image, mock=False) -> str:
    """Use Gemini to identify ingredients in an uploaded image."""
    if mock:
        logger.info("Using mock response for ingredient recognition")
        return "Tomato, Onion, Chicken, Broccoli, Rice (mock)"
    
    try:
        logger.info("Processing image for ingredient recognition")
        # Convert image to standard JPEG
        buffer = BytesIO()
        image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=85)
        image_data = buffer.getvalue()
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        prompt = "Identify all food ingredients visible in this image. List them in a comma-separated format (e.g., 'Tomato, Onion, Chicken'). Include any packaged foods if recognizable."
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}}
            ],
            generation_config={"max_output_tokens": 256}
        )
        ingredients = response.text.strip()
        if not ingredients:
            ingredients = "No ingredients identified"
        logger.info(f"Identified ingredients: {ingredients}")
        time.sleep(4)  # Delay to stay under 15 RPM (60/15=4s)
        return ingredients
    except genai.exceptions.BlockedPromptException as e:
        logger.error(f"Blocked prompt error: {e}")
        return "Error: Inappropriate content detected"
    except genai.exceptions.GoogleAPIError as e:
        logger.error(f"API error: {e}")
        if "429" in str(e):
            return "Error: Quota exceeded. Try again later or enter ingredients manually."
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"Error: {str(e)}"

def get_health_recommendation():
    """Get health recommendation data from session state"""
    if "health_recommendation" in st.session_state:
        rec = st.session_state["health_recommendation"]
        return {
            "calories": rec.get("calorie_target", "Unknown"),
            "bmi": rec.get("bmi", 0),
            "status": rec.get("weight_status", "Unknown"),
            "grocery_list": rec.get("grocery_list", "No grocery list available")
        }
    return None

def generate_full_day_meal_plan(ingredients: str, health_rec: dict = None, mock=False) -> dict:
    """Generate a full-day meal plan with calorie breakdown using Gemini."""
    if mock:
        logger.info("Using mock response for meal plan generation")
        return {
            "total_calories": 1800,
            "meals": [
                {
                    "name": "Mock Breakfast",
                    "calories": 400,
                    "ingredients": "Eggs, Spinach, Whole Wheat Toast",
                    "description": "Scrambled eggs with spinach on whole wheat toast"
                },
                {
                    "name": "Mock Lunch",
                    "calories": 600,
                    "ingredients": "Chicken, Rice, Broccoli",
                    "description": "Grilled chicken with brown rice and steamed broccoli"
                },
                {
                    "name": "Mock Dinner",
                    "calories": 500,
                    "ingredients": "Salmon, Quinoa, Asparagus",
                    "description": "Baked salmon with quinoa and roasted asparagus"
                },
                {
                    "name": "Mock Snack",
                    "calories": 300,
                    "ingredients": "Greek Yogurt, Berries",
                    "description": "Greek yogurt with mixed berries"
                }
            ],
            "analysis": "This meal plan provides balanced nutrition with adequate protein and fiber.",
            "supplement_ingredients": "Avocado, Almonds"
        }
    
    try:
        # Build nutrition constraints
        nutrition_constraints = ""
        if health_rec and health_rec["calories"] != "Unknown":
            try:
                # Extract calorie number from string
                calorie_num = int(re.search(r'\d+', health_rec["calories"]).group())
                nutrition_constraints = f"""Ensure the total daily calories are approximately {calorie_num} kcal. 
                Distribute calories across meals as:
                - Breakfast: 20-25% of total
                - Lunch: 30-35% of total
                - Dinner: 30-35% of total
                - Snacks: 10-15% of total"""
            except:
                nutrition_constraints = "Aim for a balanced distribution of calories throughout the day."
        
        # Build prompt
        prompt = f"""
        You are a nutritionist creating a personalized full-day meal plan. The user has these ingredients available:
        {ingredients}
        
        {nutrition_constraints}
        
        **Task**:
        1. Create a full-day meal plan with 4 meals: Breakfast, Lunch, Dinner, and one Snack
        2. For each meal:
           - Provide a descriptive name
           - List exact calorie count
           - List ingredients used (prioritize available ingredients)
           - Provide simple preparation instructions
        3. Calculate and display total calories
        4. Analyze how well the plan meets nutritional needs
        5. If ingredients are insufficient, suggest 2-3 additional ingredients from the user's recommended grocery list: 
           {health_rec['grocery_list'] if health_rec else 'No specific recommendations'}
        
        **Response Format** (JSON):
        {{
            "total_calories": [integer],
            "meals": [
                {{
                    "name": "Meal Name",
                    "calories": [integer],
                    "ingredients": "Ingredient1, Ingredient2",
                    "description": "Preparation instructions"
                }},
                ... # for all meals
            ],
            "analysis": "Nutritional analysis text",
            "supplement_ingredients": "Additional needed ingredients"
        }}
        """
        
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": 2048,
                "response_mime_type": "application/json"
            }
        )
        
        # Parse JSON response
        meal_plan = response.text.strip()
        try:
            import json
            return json.loads(meal_plan)
        except json.JSONDecodeError:
            # Fallback to text extraction
            return {
                "meals": [],
                "analysis": "Could not parse meal plan",
                "raw_response": meal_plan
            }
            
    except genai.exceptions.GoogleAPIError as e:
        logger.error(f"API error: {e}")
        if "429" in str(e):
            return {"error": "Quota exceeded. Try again later."}
        return {"error": f"API error: {str(e)}"}
    except Exception as e:
        logger.error(f"Error generating meal plan: {e}")
        return {"error": f"Unexpected error: {str(e)}"}

def get_youtube_videos(recipe_names: list) -> list:
    """Fetch YouTube video links for given recipe names."""
    try:
        videos = []
        for recipe in recipe_names:
            search_response = youtube_service.search().list(
                q=f"{recipe} recipe tutorial",
                part="snippet",
                maxResults=2,
                type="video",
                relevanceLanguage="en"
            ).execute()
            for item in search_response.get("items", []):
                video_id = item["id"]["videoId"]
                video_title = item["snippet"]["title"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                videos.append({"title": video_title, "url": video_url})
        logger.info(f"Found {len(videos)} YouTube videos")
        return videos
    except Exception as e:
        logger.error(f"Error fetching YouTube videos: {e}")
        return []

def display_meal_plan(plan: dict):
    """Display the meal plan with proper formatting"""
    if "error" in plan:
        st.error(plan["error"])
        return
    
    if "meals" not in plan or not plan["meals"]:
        st.warning("No meal plan generated")
        if "raw_response" in plan:
            st.text_area("Raw Response", plan["raw_response"], height=300)
        return
    
    # Display total calories
    if "total_calories" in plan:
        health_rec = get_health_recommendation()
        if health_rec and health_rec["calories"] != "Unknown":
            try:
                target_cal = int(re.search(r'\d+', health_rec["calories"]).group())
                diff = plan["total_calories"] - target_cal
                status = "✅ On target" if abs(diff) <= 100 else f"⚠️ {abs(diff)} kcal {'over' if diff > 0 else 'under'} target"
                st.subheader(f"Total Calories: {plan['total_calories']} kcal {status}")
            except:
                st.subheader(f"Total Calories: {plan['total_calories']} kcal")
    
    # Display each meal
    for meal in plan["meals"]:
        with st.expander(f"🍽️ {meal['name']} - {meal['calories']} kcal", expanded=True):
            st.markdown(f"**Ingredients**: {meal['ingredients']}")
            st.markdown(f"**Preparation**:")
            st.write(meal['description'])
    
    # Display nutritional analysis
    if "analysis" in plan:
        st.subheader("Nutritional Analysis")
        st.write(plan['analysis'])
    
    # Display supplement ingredients
    if "supplement_ingredients" in plan and plan["supplement_ingredients"]:
        st.subheader("Recommended Additional Ingredients")
        st.info(plan['supplement_ingredients'])
        if st.button("Add to Shopping List"):
            # Add to session state for later use
            st.session_state.setdefault("shopping_list", []).extend(
                [item.strip() for item in plan['supplement_ingredients'].split(",")]
            )
            st.success("Added to shopping list!")

def main():
    logger.info("Starting diet page rendering")
    st.header("🍎 Personalized Meal Planning")
    st.write("Create a customized daily meal plan based on your available ingredients and health goals")
    
    # ===== CRITICAL FIX: COMPREHENSIVE SESSION STATE CHECK =====
    required_keys = ["form_data", "symptoms_data", "goal", "health_recommendation"]
    missing_keys = [key for key in required_keys if key not in st.session_state]
    
    if missing_keys:
        st.warning(f"Please complete previous steps first. Missing: {', '.join(missing_keys)}")
        return
    # ==========================================================
    
    user_id = st.session_state["form_data"].get("full_name", "unknown")
    health_rec = get_health_recommendation()
    
    # Health summary
    with st.expander("Your Health Summary", expanded=True):
        if health_rec:
            cols = st.columns(3)
            cols[0].metric("Daily Calories", health_rec["calories"])
            cols[1].metric("BMI", f"{health_rec['bmi']:.1f}")
            cols[2].metric("Weight Status", health_rec["status"])
        else:
            st.warning("Complete Health Recommendations (Step 5) for personalized nutrition targets")
    
    # Mock mode for demo
    mock_mode = st.checkbox("Use mock responses (demo without API calls)", value=False)
    
    # Input options
    input_method = st.radio("Ingredient Input Method:", ("Upload Image", "Enter Manually"))
    ingredients = ""
    
    if input_method == "Upload Image":
        uploaded_file = st.file_uploader("Upload ingredients photo", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Your Ingredients", width=300)
            with st.spinner("Identifying ingredients..."):
                ingredients = identify_ingredients_from_image(image, mock=mock_mode)
            st.text_area("Identified Ingredients", ingredients, height=100)
    else:
        ingredients = st.text_area("Enter available ingredients (comma separated):", 
                                  "chicken, rice, broccoli, eggs, spinach, tomatoes, olive oil",
                                  height=100)
    
    # Generate meal plan
    if st.button("Generate Full-Day Meal Plan", type="primary"):
        if not ingredients or ingredients.startswith("Error"):
            st.error("Please provide valid ingredients")
            return
            
        with st.spinner("Creating your personalized meal plan..."):
            plan = generate_full_day_meal_plan(ingredients, health_rec, mock=mock_mode)
            
            # Display plan
            display_meal_plan(plan)
            
            # Get YouTube videos
            if "meals" in plan and not isinstance(plan["meals"], str):
                recipe_names = [meal["name"] for meal in plan["meals"]]
                videos = get_youtube_videos(recipe_names)
                if videos:
                    st.subheader("📺 Cooking Tutorials")
                    for video in videos:
                        st.markdown(f"- [{video['title']}]({video['url']})")
            
            # Save to history
            if "total_calories" in plan:
                try:
                    meal_text = "\n\n".join(
                        [f"{meal['name']} ({meal['calories']} kcal): {meal['description']}" 
                         for meal in plan["meals"]]
                    )
                    add_to_health_history(
                        user_id=user_id,
                        report_type="Meal Plan",
                        text=f"Total Calories: {plan['total_calories']}\n\n{meal_text}",
                        tables=[]
                    )
                    st.success("Meal plan saved to your health history!")
                except Exception as e:
                    st.error(f"Failed to save meal plan: {str(e)}")
    
    # Display shopping list if exists
    if "shopping_list" in st.session_state and st.session_state["shopping_list"]:
        st.subheader("🛒 Your Shopping List")
        for i, item in enumerate(set(st.session_state["shopping_list"])):
            st.checkbox(f"{item}", key=f"shop_item_{i}")

if __name__ == "__main__":
    main()