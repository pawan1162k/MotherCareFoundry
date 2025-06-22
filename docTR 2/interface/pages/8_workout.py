import streamlit as st
from utils.logger import setup_logger
from prognosis.llm import process_workout_data
from storage.chroma_db import add_to_health_history
import datetime
import requests
import json
import os  # Added import for environment variables

logger = setup_logger("workout")

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("streamlit/assets/style.css")

def get_youtube_videos(exercise_names: list) -> list:
    """Fetch YouTube video links for given exercise names."""
    # Fixed environment variable handling
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    if not YOUTUBE_API_KEY:
        logger.error("YOUTUBE_API_KEY not found")
        return []
    
    try:
        videos = []
        for exercise in exercise_names:
            # Search for exercise tutorial
            search_url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": f"{exercise} exercise tutorial",
                "type": "video",
                "maxResults": 1,
                "key": YOUTUBE_API_KEY
            }
            response = requests.get(search_url, params=params)
            data = response.json()
            
            for item in data.get("items", []):
                video_id = item["id"]["videoId"]
                video_title = item["snippet"]["title"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                thumbnail = item["snippet"]["thumbnails"]["medium"]["url"]
                videos.append({
                    "title": video_title,
                    "url": video_url,
                    "thumbnail": thumbnail,
                    "exercise": exercise
                })
        logger.info(f"Found {len(videos)} YouTube videos")
        return videos
    except Exception as e:
        logger.error(f"Error fetching YouTube videos: {e}")
        return []

def extract_exercises(workout_details: str) -> list:
    """Extract exercise names from workout details text"""
    try:
        # Try to parse as JSON first
        exercises = json.loads(workout_details)
        if isinstance(exercises, list):
            return [ex["name"] for ex in exercises]
    except:
        pass
    
    # Fallback to text parsing
    import re
    exercises = []
    lines = workout_details.split('\n')
    for line in lines:
        # Look for lines that seem to describe exercises
        match = re.match(r"^\d+\.\s*(.+?)\s*-\s*", line)
        if match:
            exercises.append(match.group(1).strip())
        elif ":" in line:
            exercises.append(line.split(":")[0].strip())
    
    return exercises[:5]  # Return max 5 exercises

def display_day_workout(day: dict):
    """Display a day's workout with videos"""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Focus:** {day['focus']}")
        st.markdown(f"**Duration:** {day['duration']}")
        st.markdown(f"**Calorie Burn:** {day['calorie_burn']}")
        st.markdown("**Workout:**")
        st.write(day['details'])
    
    with col2:
        if "videos" in day:
            for video in day["videos"]:
                st.image(video["thumbnail"], width=120)
                st.markdown(f"[{video['title']}]({video['url']})", unsafe_allow_html=True)

def main():
    st.header("💪 Your Personalized Workout Plan")
    st.info("Build strength and endurance with a plan tailored to your fitness level and goals")
    
    # ===== CRITICAL FIX: COMPREHENSIVE SESSION STATE CHECK =====
    required_keys = ["form_data", "symptoms_data", "goal", "health_recommendation"]
    missing_keys = [key for key in required_keys if key not in st.session_state]
    
    if missing_keys:
        st.warning(f"Please complete previous steps first. Missing: {', '.join(missing_keys)}")
        return
    # ==========================================================
    
    # Get data with consistent keys
    profile = st.session_state["form_data"]
    goal = st.session_state["goal"]
    health_rec = st.session_state["health_recommendation"]
    
    # Workout type selection
    st.subheader("Workout Preferences")
    workout_type = st.radio("Select your workout environment:", 
                           ("🏠 Home Workout (No Equipment)", 
                            "🏋️ Gym Workout (Full Equipment)", 
                            "🔄 Hybrid (Some Equipment)"),
                           index=0)
    
    intensity = st.slider("Workout Intensity", 1, 5, 3, 
                         help="1 = Beginner, 3 = Intermediate, 5 = Advanced")
    
    # Display fitness summary
    with st.expander("📊 Your Fitness Profile", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Goal", goal["type"].split()[0])
        with col2:
            # Fixed key to match results.py
            st.metric("Calorie Target", f"{health_rec.get('calorie_target', 'Unknown')} kcal")
        with col3:
            st.metric("Activity Level", profile["activity_level"].split("(")[0].strip())
    
    # Generate workout plan
    if st.button("Generate Workout Plan", type="primary"):
        with st.spinner("Creating your personalized workout plan..."):
            workout_data = {
                "profile": profile,
                "goal": goal,
                "health_recommendation": health_rec,
                "workout_type": workout_type,
                "intensity": intensity
            }
            workout_plan = process_workout_data(workout_data)
            
            # Add videos to each day's workout
            if "schedule" in workout_plan:
                for day in workout_plan["schedule"]:
                    exercises = extract_exercises(day.get("details", ""))
                    day["videos"] = get_youtube_videos(exercises)
            
            st.session_state["workout_plan"] = workout_plan
            logger.info(f"Workout plan generated with {len(workout_plan.get('schedule', []))} days")
    
    # Display workout plan
    if "workout_plan" in st.session_state:
        workout_plan = st.session_state["workout_plan"]
        
        st.subheader("Your Weekly Workout Plan")
        st.markdown(f"**Calorie Burn Target:** {workout_plan.get('calorie_burn_target', 'Unknown')} kcal per day")
        st.markdown(f"**Plan Overview:**")
        st.info(workout_plan.get('overview', 'No overview available'))
        
        st.divider()
        
        # Day navigation
        days = workout_plan.get("schedule", [])
        if days:
            tab_names = [f"Day {i+1}" for i in range(len(days))]
            tabs = st.tabs(tab_names)
            
            for i, tab in enumerate(tabs):
                with tab:
                    display_day_workout(days[i])
        
        # Progress tracking
        st.divider()
        st.subheader("Track Your Progress")
        if st.button("✅ Completed Today's Workout"):
            st.balloons()
            st.success("Great job! Your progress has been recorded.")
        
        # Download and save options
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Download Workout Plan", type="secondary"):
                workout_text = (
                    f"Calorie Burn Target: {workout_plan['calorie_burn_target']}\n"
                    f"Overview: {workout_plan['overview']}\n\n"
                    "Daily Schedule:\n"
                )
                for i, day in enumerate(days, 1):
                    workout_text += (
                        f"\nDay {i}: {day['focus']}\n"
                        f"Duration: {day['duration']}\n"
                        f"Calorie Burn: {day['calorie_burn']}\n"
                        f"Details: {day['details']}\n"
                    )
                
                st.download_button(
                    "Download Plan",
                    data=workout_text,
                    file_name=f"workout_plan_{datetime.date.today()}.txt",
                    mime="text/plain"
                )
        
        with col2:
            if st.button("💾 Save to Fitness History", type="secondary"):
                try:
                    workout_text = f"Workout Type: {workout_type}\nIntensity: {intensity}/5\n"
                    for i, day in enumerate(days, 1):
                        workout_text += f"\nDay {i}: {day['focus']} ({day['calorie_burn']})"
                    
                    add_to_health_history(
                        user_id=profile.get("full_name", "unknown"),
                        report_type="Workout Plan",
                        text=workout_text,
                        tables=[]
                    )
                    st.success("Workout plan saved to your fitness history!")
                except Exception as e:
                    st.error(f"Failed to save workout plan: {str(e)}")
        
        st.divider()
        st.info("**Safety First**: Consult with a healthcare provider before starting any new exercise program. Stop immediately if you experience pain.")

if __name__ == "__main__":
    main()