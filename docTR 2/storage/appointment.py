import random
from utils.logger import setup_logger

logger = setup_logger("appointment")

# Mock doctor database
DOCTORS = [
    {
        "name": "Dr. Alice Smith",
        "specialty": "General Practitioner",
        "location": "New York",
        "phone": "555-0101",
        "email": "alice@example.com"
    },
    {
        "name": "Dr. Bob Johnson",
        "specialty": "Nutrition Specialist",
        "location": "Los Angeles",
        "phone": "555-0102",
        "email": "bob@example.com"
    },
    {
        "name": "Dr. Carol Williams",
        "specialty": "Health Coach",
        "location": "Chicago",
        "phone": "555-0103",
        "email": "carol@example.com"
    },
    {
        "name": "Dr. David Kim",
        "specialty": "Sports Medicine",
        "location": "Miami",
        "phone": "555-0104",
        "email": "david@example.com"
    }
]

def get_doctors_for_booking(condition: str, location: str, n_results: int = 3) -> list:
    """Get a list of doctors matching the condition and location"""
    try:
        # Filter doctors by location
        filtered = [doc for doc in DOCTORS if location.lower() in doc["location"].lower()]
        
        # If no doctors in exact location, return any doctors
        if not filtered:
            filtered = DOCTORS
        
        # Return requested number of results
        return filtered[:n_results]
    except Exception as e:
        logger.error(f"Error getting doctors: {e}")
        return DOCTORS[:n_results]  # Return default doctors on error

def book_appointment(doctor: dict, patient_data: dict) -> str:
    """Book an appointment with a doctor (simulated)"""
    try:
        patient_name = patient_data.get("form_data", {}).get("full_name", "Patient")
        doctor_name = doctor["name"]
        
        # Generate random appointment time
        times = ["10:00 AM", "2:30 PM", "4:15 PM", "11:45 AM"]
        appointment_time = random.choice(times)
        booking_id = f"APT-{random.randint(1000,9999)}"
        
        return (
            f"Appointment confirmed with {doctor_name}!\n\n"
            f"**Booking ID:** {booking_id}\n"
            f"**Time:** Tomorrow at {appointment_time}\n"
            f"**Location:** {doctor['location']}\n\n"
            "You'll receive a confirmation email shortly."
        )
    except Exception as e:
        logger.error(f"Failed to book appointment: {e}")
        return "Failed to book appointment. Please try again later."