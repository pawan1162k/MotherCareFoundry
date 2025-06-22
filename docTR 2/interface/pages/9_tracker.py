import streamlit as st
from utils.logger import setup_logger
import datetime
import calendar
import pandas as pd
import numpy as np
import time
import random
import os

logger = setup_logger("tracker")

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("streamlit/assets/style.css")

# Mock partner rewards - would come from a DB in production
PARTNER_REWARDS = [
    {"name": "Protein Shake", "partner": "GNC", "points": 50, "description": "Free protein shake at any GNC store"},
    {"name": "Yoga Mat", "partner": "Decathlon", "points": 200, "description": "20% off on yoga mats"},
    {"name": "Gym Session", "partner": "Gold's Gym", "points": 100, "description": "Free day pass"},
    {"name": "Smoothie", "partner": "Juice Bar", "points": 75, "description": "Free superfood smoothie"},
    {"name": "Fitness Tracker", "partner": "FitBit", "points": 500, "description": "15% off on all trackers"}
]

def get_streak_data(patient_id):
    """Get or initialize streak data in session state"""
    if "streak_data" not in st.session_state:
        st.session_state.streak_data = {
            "current_streak": 0,
            "longest_streak": 0,
            "last_completed": None,
            "completed_days": set(),
            "points": 100  # Starting points
        }
    return st.session_state.streak_data

def mark_completed(patient_id):
    """Mark today as completed and update streak"""
    streak_data = get_streak_data(patient_id)
    today = datetime.date.today()
    
    # If we already completed today, do nothing
    if today in streak_data["completed_days"]:
        return False
    
    # Check if we're continuing a streak
    yesterday = today - datetime.timedelta(days=1)
    if streak_data["last_completed"] == yesterday:
        streak_data["current_streak"] += 1
    else:
        streak_data["current_streak"] = 1
    
    # Update records
    streak_data["completed_days"].add(today)
    streak_data["last_completed"] = today
    
    # Update longest streak
    if streak_data["current_streak"] > streak_data["longest_streak"]:
        streak_data["longest_streak"] = streak_data["current_streak"]
    
    # Award points
    streak_data["points"] += 20  # Base points
    streak_data["points"] += streak_data["current_streak"] * 5  # Streak bonus
    
    # Random bonus chance
    if random.random() < 0.3:  # 30% chance
        bonus = random.randint(10, 50)
        streak_data["points"] += bonus
        return True, bonus
    
    return True, 0

def generate_streak_calendar(year, month, completed_days):
    """Generate a visual calendar with streak highlights"""
    cal = calendar.monthcalendar(year, month)
    today = datetime.date.today()
    
    # Create calendar display
    st.subheader(f"{calendar.month_name[month]} {year}")
    cols = st.columns(7)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    # Header with day names
    for i, col in enumerate(cols):
        col.write(f"**{day_names[i]}**")
    
    # Create rows for each week
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write(" ")
                continue
                
            date = datetime.date(year, month, day)
            is_today = (date == today)
            is_completed = date in completed_days
            
            # Style based on status
            if is_completed:
                cols[i].success(f"✓ {day}")
            elif is_today:
                cols[i].info(f"★ {day}")
            elif date < today:
                cols[i].error(f"{day}")
            else:
                cols[i].write(f"{day}")

def plot_progress_chart():
    """Show progress charts"""
    # Mock data - would come from DB in production
    days = 30
    dates = [datetime.date.today() - datetime.timedelta(days=i) for i in range(days, 0, -1)]
    workout_data = [random.randint(20, 100) for _ in range(days)]
    nutrition_data = [random.randint(50, 100) for _ in range(days)]
    recovery_data = [random.randint(60, 100) for _ in range(days)]
    
    # Create dataframe
    df = pd.DataFrame({
        "Date": dates,
        "Workout Completion": workout_data,
        "Nutrition Score": nutrition_data,
        "Recovery Quality": recovery_data
    }).set_index("Date")
    
    # Plot
    st.subheader("Progress Over Last 30 Days")
    st.line_chart(df)

def main():
    st.header("🏆 Your Fitness Tracker")
    st.info("Track your progress, maintain streaks, and earn rewards for healthy habits!")
    
    # Check for required data
    required_keys = ["form_data"]
    missing_keys = [key for key in required_keys if key not in st.session_state]
    
    if missing_keys:
        st.warning(f"Please complete Step 1: Health Profile first")
        return
    
    user_data = st.session_state["form_data"]
    patient_id = user_data.get("full_name", "default_user")
    
    # Initialize streak data
    streak_data = get_streak_data(patient_id)
    
    # Main columns layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Streak info card
        st.subheader("🔥 Your Streak")
        st.metric("Current Streak", f"{streak_data['current_streak']} days")
        st.metric("Longest Streak", f"{streak_data['longest_streak']} days")
        st.metric("Total Points", f"{streak_data['points']}")
        
        # Mark completion section
        st.divider()
        today = datetime.date.today()
        
        if today in streak_data["completed_days"]:
            st.success("✅ Today completed!")
            st.balloons()
        else:
            if st.button("🎯 Mark Today as Completed", type="primary", use_container_width=True):
                completed, bonus = mark_completed(patient_id)
                if completed:
                    if bonus > 0:
                        st.success(f"✅ Today completed! +{bonus} bonus points!")
                    else:
                        st.success("✅ Today completed!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
        
        # Rewards section
        st.divider()
        st.subheader("🏅 Your Rewards")
        st.caption(f"You have {streak_data['points']} points")
        
        for reward in PARTNER_REWARDS:
            with st.expander(f"{reward['name']} ({reward['points']} pts)"):
                st.write(f"**Partner**: {reward['partner']}")
                st.write(f"**Description**: {reward['description']}")
                if streak_data["points"] >= reward["points"]:
                    if st.button(f"Redeem with {reward['partner']}", key=f"redeem_{reward['name']}"):
                        streak_data["points"] -= reward["points"]
                        st.success(f"🎉 Reward claimed! Check your email for your {reward['name']} coupon.")
                        time.sleep(2)
                        st.rerun()
                else:
                    st.warning(f"You need {reward['points'] - streak_data['points']} more points")
    
    with col2:
        # Streak calendar
        today = datetime.date.today()
        generate_streak_calendar(today.year, today.month, streak_data["completed_days"])
        
        # Progress charts
        st.divider()
        plot_progress_chart()
        
        # Achievement badges
        st.divider()
        st.subheader("🏆 Achievements")
        
        badges = [
            {"name": "First Step", "earned": True, "desc": "Complete your first day"},
            {"name": "Week Warrior", "earned": streak_data["current_streak"] >= 7, "desc": "7-day streak"},
            {"name": "Month Master", "earned": streak_data["longest_streak"] >= 30, "desc": "30-day streak"},
            {"name": "Nutrition Ninja", "earned": False, "desc": "Perfect nutrition week"},
            {"name": "Workout Warrior", "earned": False, "desc": "Complete all weekly workouts"}
        ]
        
        cols = st.columns(len(badges))
        for i, badge in enumerate(badges):
            with cols[i]:
                if badge["earned"]:
                    st.success(f"★ {badge['name']}")
                else:
                    st.info(f"☆ {badge['name']}")
                st.caption(badge["desc"])

if __name__ == "__main__":
    main()