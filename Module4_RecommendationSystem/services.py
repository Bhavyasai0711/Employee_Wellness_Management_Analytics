import os
import requests
import urllib.request
import urllib.error
import json
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from database import db
from datetime import datetime

from Module2_EmployeeHealthData.models import EmployeeHealth
from Module4_RecommendationSystem.models import WellnessReminder

# Database model for persisting the Generative AI Wellness Plans
class WellnessPlan(db.Model):
    __tablename__ = "wellness_plans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True)
    plan_text = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_content_based_recommendations(record):
    recs = {
        "fitness": [],
        "diet": [],
        "mental_wellness": [],
        "yoga": []
    }
    
    # 1. Fitness Plans
    if record.bmi >= 25.0:
        recs["fitness"].append({
            "title": "Cardio Weight Management Program",
            "duration": "35-45 minutes / session",
            "frequency": "4-5 days/week",
            "details": "Focus on low-impact, fat-burning cardiovascular exercises such as brisk walking, cycling, or swimming to manage BMI."
        })
        recs["fitness"].append({
            "title": "Full Body Resistance Training",
            "duration": "20 minutes / session",
            "frequency": "2 days/week",
            "details": "Light bodyweight resistance (squats, lunges, planks) to increase basal metabolic rate."
        })
    else:
        recs["fitness"].append({
            "title": "General Cardiovascular Conditioning",
            "duration": "25-30 minutes / session",
            "frequency": "3 days/week",
            "details": "Standard heart rate conditioning using jogging, elliptical, or rowers."
        })
        recs["fitness"].append({
            "title": "Core and Core Stability Workouts",
            "duration": "15 minutes / session",
            "frequency": "3 days/week",
            "details": "Core training to improve posture, balance, and lower back stability."
        })

    # 2. Diet & Nutrition
    if record.bmi >= 25.0:
        recs["diet"].append({
            "title": "Calorie-Deficit Nutrition Schedule",
            "calories": "~1800 kcal / day",
            "details": "Focus on high-protein, high-fiber foods to support metabolic health. Restrict refined sugars and high-carb processed meals."
        })
    elif record.blood_sugar and record.blood_sugar > 140.0:
        recs["diet"].append({
            "title": "Low-Glycemic Diet (Blood Sugar Management)",
            "calories": "Balanced intake",
            "details": "Incorporate complex carbohydrates (oats, quinoa), leafy greens, healthy fats, and restrict simple sugars to regulate glucose."
        })
    else:
        recs["diet"].append({
            "title": "Balanced Whole-Foods Meal Prep Plan",
            "calories": "Maintenance target (~2200 kcal)",
            "details": "Include lean proteins, whole grains, nuts, and diverse vegetables to preserve overall wellness index."
        })
        
    water_target = "3.2 Litres" if record.bmi >= 25 else "2.5 Litres"
    recs["diet"].append({
        "title": "Hydration Optimization",
        "calories": "0 kcal",
        "details": f"Target drinking {water_target} of water daily. Set hydration reminders every 2 hours."
    })

    # 3. Mental Wellness & Mindfulness
    if record.stress_level in ("High", "Severe"):
        recs["mental_wellness"].append({
            "title": "Mindfulness Breathing & Grounding Exercise",
            "schedule": "15 minutes daily (Morning/Before bed)",
            "details": "Practice box breathing (inhale 4s, hold 4s, exhale 4s, hold 4s) to decrease autonomic stress spikes."
        })
        recs["mental_wellness"].append({
            "title": "Daily Guided Meditation Sessions",
            "schedule": "10-15 minutes (Mid-day stress relief)",
            "details": "Use body-scan or mindfulness meditations to disengage from workplace cognitive loads."
        })
    else:
        recs["mental_wellness"].append({
            "title": "Gratitude Journaling",
            "schedule": "5 minutes (End of day)",
            "details": "Document three successful events or achievements daily to build psychological resilience."
        })

    # 4. Yoga Sessions
    if record.stress_level in ("High", "Severe"):
        recs["yoga"].append({
            "title": "Restorative / Yin Yoga Poses",
            "duration": "20 minutes session",
            "details": "Hold restorative poses like Child's Pose (Balasana), Legs-Up-the-Wall (Viparita Karani), and Bridge Pose to lower cortisol levels."
        })
    else:
        recs["yoga"].append({
            "title": "Vinyasa Flow / Sun Salutations",
            "duration": "15 minutes session",
            "details": "Dynamic sequence of Sun Salutations (Surya Namaskar) to improve full-body flexibility and energy flow."
        })
    # 5. YouTube Video Recommendations
    recs["video_recommendations"] = [
        {
            "title": "How Workplace Wellness Programs Benefit Employees",
            "embed_url": "https://www.youtube.com/embed/vF2emoRdCPs",
            "watch_url": "https://www.youtube.com/watch?v=vF2emoRdCPs",
            "badge": "3 Min Overview",
            "category": "Workplace Wellness",
            "details": "A short workplace wellness video explaining how structured wellness programs improve employee health, morale, and engagement."
        },
        {
            "title": "Corporate Yoga & Stress Management Podcast",
            "embed_url": "https://www.youtube.com/embed/F44zYHCaXZA",
            "watch_url": "https://www.youtube.com/watch?v=F44zYHCaXZA",
            "badge": "Expert Podcast",
            "category": "Yoga & Stress",
            "details": "A workplace wellness podcast discussing stress reduction, yoga practices, and physical health for corporate professionals."
        }
    ]
        
    return recs


def get_collaborative_recommendations(user_record):
    records = EmployeeHealth.query.filter(EmployeeHealth.user_id != user_record.user_id).all()
    
    if len(records) < 3:
        # Fallback recommendations if user count is too small to calculate similarity
        return [
            "Add a 15-minute brisk walk after lunch (reported high success among other employees).",
            "Practice desk shoulder rolls and neck stretches during screen breaks.",
            "Integrate herbal tea to support hydration and stress reduction."
        ]
        
    # Build feature vectors for cosine similarity calculation
    # Attributes: age, bmi, sleep_hours, heart_rate, attendance_percentage
    data = []
    for r in records:
        data.append([r.age, r.bmi, r.sleep_hours, r.heart_rate, r.attendance_percentage])
        
    df = pd.DataFrame(data, columns=["age", "bmi", "sleep", "heart_rate", "attendance"])
    
    user_vector = np.array([[
        user_record.age,
        user_record.bmi,
        user_record.sleep_hours,
        user_record.heart_rate,
        user_record.attendance_percentage
    ]])
    
    # Calculate similarities
    sims = cosine_similarity(user_vector, df)[0]
    top_indices = np.argsort(sims)[::-1][:3] # Top 3 similar profiles
    
    recommendations = []
    seen_remarks = set()
    for idx in top_indices:
        peer_record = records[idx]
        
        # Pull peer's exercise habits
        routine = f"Peer profile match ({peer_record.user.department} Dept): Integrates '{peer_record.exercise_type or 'Cardio'}' ({peer_record.exercise_frequency}) into daily routines."
        if routine not in seen_remarks:
            recommendations.append(routine)
            seen_remarks.add(routine)
            
        # Pull physician notes or general remarks if positive
        if peer_record.doctor_remarks and len(peer_record.doctor_remarks) > 10 and peer_record.doctor_remarks not in seen_remarks:
            recommendations.append(f"Lifestyle Tip: {peer_record.doctor_remarks}")
            seen_remarks.add(peer_record.doctor_remarks)
            
    # Guarantee at least 3 tips
    if len(recommendations) < 3:
        recommendations.append("Join the local workplace step challenge to support daily active calorie tracking.")
        
    return recommendations


def generate_qwen_ai_plan(record):
    prompt_payload = {
        "model": "qwen2.5:0.5b",
        "prompt": f"""You are a certified employee wellness and sports medicine coach. Generate a detailed, highly encouraging Personal Wellness Plan for an employee based on the following biometric metrics:
- Age: {record.age} years
- Gender: {record.gender}
- BMI: {record.bmi} ({record.bmi_category})
- Blood Pressure: {record.blood_pressure} mmHg
- Resting Heart Rate: {record.heart_rate} bpm
- Sleep Duration: {record.sleep_hours} hours/day
- Self-reported Stress level: {record.stress_level}
- Average Daily Steps: {record.daily_step_count or 'Unknown'}
- Medical Conditions: {record.medical_conditions or 'None'}

Formatting: Provide clear headings in Markdown format:
### 1. Tailored Cardio & Strength Workout
### 2. Metabolic Diet Schedule & Calorie Strategy
### 3. Stress-Reduction Yoga & Meditation Poses
### 4. Direct Coaching Recommendations
""",
        "stream": False
    }
    
    # Fire HTTP REST POST request to local Ollama API
    try:
        url = "http://127.0.0.1:11434/api/generate"
        req = urllib.request.Request(
            url,
            data=json.dumps(prompt_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        # Set a 15-second timeout to check connection speed
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            ai_plan = res_data.get("response")
            if ai_plan:
                return ai_plan
    except Exception as e:
        print("Local Qwen API offline or timed out, returning offline generative template:", e)
        
    # Return formatted fallback plan matching user biometrics
    workout_advice = "35-minute fat-burning walks or cycling sessions" if record.bmi >= 25 else "30-minute cardio runs or strength routines"
    diet_advice = "Incorporate low-carbohydrate, high-protein meals with plenty of green vegetables." if record.bmi >= 25 else "Maintain balanced protein, carbs, and healthy fats."
    stress_advice = "Practice restorative Child's pose, Box Breathing, and 15-minute mindfulness sessions." if record.stress_level in ("High", "Severe") else "Practice active Vinyasa yoga sequences and dynamic stretching."
    
    fallback_plan = f"""### 1. Tailored Cardio & Strength Workout
*   **Cardio Program**: Engage in **{workout_advice}** at least 3-4 days per week.
*   **Strength Work**: Run light bodyweight squat and core plank interval sessions 2 days per week to support postural muscle toning and raise base metabolic rates.

### 2. Metabolic Diet Schedule & Calorie Strategy
*   **Nutrition Guidelines**: {diet_advice}
*   **Hydration Target**: Restructure water intake to reach **{ '3.2' if record.bmi >= 25 else '2.5' } Litres** of water per day. Limit coffee intake if heart rate exceeds 90 bpm.

### 3. Stress-Reduction Yoga & Meditation Poses
*   **Recommended Exercises**: {stress_advice}
*   **Breathing Intervals**: Implement 4-7-8 breathing patterns during office screen breaks to regulate cardiovascular stress.

### 4. Direct Coaching Recommendations
*   Your calculated Wellness Index indicates active progress. Target sleeping at least 7.5 hours per night to maximize physical recovery.
"""
    return fallback_plan


def get_video_and_animation_recommendations(record):
    video_recs = []

    # 1. Box Breathing Interactive Animation Guide
    video_recs.append({
        "id": "anim-breathing",
        "title": "4-7-8 Box Breathing Visualizer (Animation)",
        "category": "Mindfulness & Stress Relief",
        "type": "Interactive Animation",
        "duration": "5 Minutes",
        "thumbnail_icon": "fa-wind",
        "accent_color": "#7c3aed",
        "badge": "Interactive Visualizer",
        "description": "Dynamic breathing animation loop. Inhale for 4 seconds, hold for 7 seconds, and exhale for 8 seconds to lower heart rate and reduce cortisol.",
        "animation_type": "breathing_circle",
        "video_url": "https://www.youtube.com/embed/tEmt1Znux58",
        "transcript": "Welcome to the 4-7-8 Box Breathing animation guide. Follow the expanding purple circle. Inhale slowly through your nose for 4 seconds. Hold your breath for 7 seconds. Slowly exhale through your mouth for 8 seconds. Repeat for 5 cycles to relieve stress."
    })

    # 2. Desk Ergonomics & Spinal Stretch Video Guide
    video_recs.append({
        "id": "video-desk-stretch",
        "title": "5-Minute Workplace Desk Stretch (Video)",
        "category": "Ergonomics & Flexibility",
        "type": "HD Video Guide",
        "duration": "5 Minutes",
        "thumbnail_icon": "fa-person-shelter",
        "accent_color": "#059669",
        "badge": "Desk Friendly",
        "description": "Guided workplace posture stretches to relieve lumbar pressure, neck stiffness, and wrist strain caused by prolonged desk screen time.",
        "animation_type": "desk_stretch_loop",
        "video_url": "https://www.youtube.com/embed/M-8FvC3GD8c",
        "transcript": "5-minute workplace desk stretch video guide. Sitting upright, roll your shoulders back 5 times. Slowly tilt your head side to side to stretch neck muscles. Interlock your fingers and stretch arms overhead. Extend wrist flexors to reduce screen fatigue."
    })

    # 3. HIIT Fat Burn & Cardio Animation Guide
    if record.bmi >= 25.0:
        video_recs.append({
            "id": "video-hiit",
            "title": "Fat-Burning HIIT Cardio Step Routine (Video & Animation)",
            "category": "Fitness & Weight Loss",
            "type": "Animated Motion & Video",
            "duration": "15 Minutes",
            "thumbnail_icon": "fa-fire-flame-curved",
            "accent_color": "#dc2626",
            "badge": "High Calorie Burn",
            "description": "High-energy, low-impact HIIT routine focusing on jumping jacks, high knees, and bodyweight squats for maximum metabolic calorie burn.",
            "animation_type": "cardio_step_loop",
            "video_url": "https://www.youtube.com/embed/ml6cT4AZdqI",
            "transcript": "15-minute fat burning HIIT routine. Perform 45 seconds of low-impact jumping jacks followed by 15 seconds rest. Next, 45 seconds of bodyweight squats keeping knees aligned over toes. Finish with light jogging in place."
        })
    else:
        video_recs.append({
            "id": "video-cardio",
            "title": "Core & Cardio Energy Booster (Video)",
            "category": "Fitness & Vitals",
            "type": "Animated Motion & Video",
            "duration": "10 Minutes",
            "thumbnail_icon": "fa-heart-pulse",
            "accent_color": "#2563eb",
            "badge": "Cardio Stamina",
            "description": "10-minute aerobic conditioning routine to boost heart rate variability, lung capacity, and mental energy levels.",
            "animation_type": "cardio_step_loop",
            "video_url": "https://www.youtube.com/embed/gC_L9qAHVJ8",
            "transcript": "10-minute core and cardio booster. Start with 1 minute of light jogging, followed by plank shoulder taps and standing bicycle crunches to build stamina."
        })

    # 4. Sun Salutation & Restorative Yoga Video Guide
    video_recs.append({
        "id": "video-yoga",
        "title": "Restorative Sun Salutation Yoga Flow (Video)",
        "category": "Yoga & Flex",
        "type": "HD Video Guide",
        "duration": "12 Minutes",
        "thumbnail_icon": "fa-child-yoga",
        "accent_color": "#d97706",
        "badge": "Flexibility & Posture",
        "description": "Guided Vinyasa yoga movement linking deep nasal breathing with spinal extension, Downward Dog, and Cobra pose.",
        "animation_type": "yoga_flow_loop",
        "video_url": "https://www.youtube.com/embed/v7AYKMP6rOE",
        "transcript": "12-minute restorative Sun Salutation yoga guide. Begin standing tall in Mountain Pose. Inhale hands upward, exhale fold forward. Step back to Plank, lower to Cobra pose, and lift hips into Downward Facing Dog."
    })

    return video_recs


def build_wellness_reminders(record):
    reminders = []

    if record.sleep_hours < 6:
        reminders.append({
            "title": "Prioritize sleep recovery",
            "message": "Your sleep hours are below the ideal range. Aim for a 7.5-hour target and keep a consistent bedtime routine.",
            "priority": "high",
            "frequency": "daily",
        })

    if record.daily_water_litres < 2.5:
        reminders.append({
            "title": "Hydration check-in",
            "message": "Your water intake is low for the day. Set a reminder every 2 hours to maintain hydration and improve focus.",
            "priority": "medium",
            "frequency": "daily",
        })

    if record.exercise_frequency in ("Never", "1-2 days/week"):
        reminders.append({
            "title": "Movement reminder",
            "message": "Try a short 20-minute walk or mobility session today to lift your wellness score and reduce fatigue.",
            "priority": "medium",
            "frequency": "daily",
        })

    if record.stress_level in ("High", "Severe"):
        reminders.append({
            "title": "Stress relief prompt",
            "message": "Your stress level is elevated. Schedule a short breathing or meditation break before the next meeting.",
            "priority": "high",
            "frequency": "daily",
        })

    if record.blood_sugar and record.blood_sugar > 140:
        reminders.append({
            "title": "Blood sugar alert",
            "message": "Your blood sugar reading is above the healthy range. Consider a lighter lunch, hydration, and a gentle walk after meals.",
            "priority": "high",
            "frequency": "daily",
        })

    if record.daily_step_count is not None and record.daily_step_count < 4000:
        reminders.append({
            "title": "Step goal reminder",
            "message": "Your step count is below the recommended daily target. Take two short walking breaks to boost energy and reduce sedentary time.",
            "priority": "medium",
            "frequency": "daily",
        })

    if record.attendance_percentage < 85:
        reminders.append({
            "title": "Attendance wellness check",
            "message": "Your attendance trend is lower than expected. Prioritize rest and recovery so your energy remains steady throughout the day.",
            "priority": "low",
            "frequency": "weekly",
        })

    if not reminders:
        reminders.append({
            "title": "Steady wellness check",
            "message": "Your current metrics are in a good range. Keep the streak going with your existing sleep, hydration, and movement routine.",
            "priority": "low",
            "frequency": "weekly",
        })

    return reminders


def sync_wellness_reminders(record):
    reminders = build_wellness_reminders(record)
    existing = WellnessReminder.query.filter_by(user_id=record.user_id).all()

    for reminder in existing:
        reminder.is_active = False

    for reminder in reminders:
        current = WellnessReminder.query.filter_by(user_id=record.user_id, title=reminder["title"]).first()
        if current:
            current.message = reminder["message"]
            current.priority = reminder["priority"]
            current.frequency = reminder["frequency"]
            current.is_active = True
        else:
            db.session.add(WellnessReminder(
                user_id=record.user_id,
                title=reminder["title"],
                message=reminder["message"],
                reminder_type="wellness",
                priority=reminder["priority"],
                frequency=reminder["frequency"],
                is_active=True,
                is_read=False,
            ))

    db.session.commit()
    return WellnessReminder.query.filter_by(user_id=record.user_id, is_active=True).order_by(WellnessReminder.priority.desc()).all()
