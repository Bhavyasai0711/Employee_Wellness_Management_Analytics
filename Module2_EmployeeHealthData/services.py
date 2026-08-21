from collections import Counter

from sqlalchemy import or_

from database import db
from models.user import User
from Module2_EmployeeHealthData.models import EmployeeHealth
from Module2_EmployeeHealthData.utils import parse_date, safe_float, safe_int


def calculate_bmi(height_cm, weight_kg):
    height_m = height_cm / 100
    return round(weight_kg / (height_m * height_m), 2)


def get_bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def _exercise_points(value):
    return {
        "Never": 0,
        "1-2 days/week": 12,
        "3-4 days/week": 20,
        "5+ days/week": 24,
        "Daily": 26,
    }.get(value, 8)


def _stress_penalty(value):
    return {
        "Low": 0,
        "Moderate": 8,
        "High": 18,
        "Severe": 28,
    }.get(value, 10)


def calculate_wellness_score(sleep, exercise_frequency, water, attendance, stress_level):
    sleep_score = min(24, max(0, sleep / 8 * 24))
    water_score = min(20, max(0, water / 3 * 20))
    attendance_score = min(20, max(0, attendance / 100 * 20))
    exercise_score = _exercise_points(exercise_frequency)
    score = sleep_score + water_score + attendance_score + exercise_score - _stress_penalty(stress_level)
    return round(max(0, min(100, score)), 1)


def calculate_health_risk_score(record_data):
    risk = 0
    bmi = record_data["bmi"]
    if bmi < 18.5 or bmi >= 30:
        risk += 25
    elif bmi >= 25:
        risk += 15
    if record_data["stress_level"] in ("High", "Severe"):
        risk += 20
    if record_data["sleep_hours"] < 6:
        risk += 15
    if record_data["attendance_percentage"] < 75:
        risk += 15
    if record_data["heart_rate"] < 50 or record_data["heart_rate"] > 110:
        risk += 10
    if record_data.get("blood_sugar") and record_data["blood_sugar"] > 140:
        risk += 10
    if record_data.get("cholesterol") and record_data["cholesterol"] > 200:
        risk += 10
    return round(min(100, risk), 1)


def build_record_data(form, user, record=None):
    def get_val(key, default_val=None):
        raw_val = form.get(key) if hasattr(form, "get") else (form[key] if key in form else None)
        if raw_val is not None and str(raw_val).strip() != "":
            return raw_val
        if record is not None and hasattr(record, key):
            rec_val = getattr(record, key)
            if rec_val is not None:
                return rec_val
        return default_val

    height = safe_float(get_val("height_cm", 170.0))
    weight = safe_float(get_val("weight_kg", 70.0))
    bmi = round(weight / ((height / 100) ** 2), 2)
    
    data = {
        "user_id": user.id,
        "employee_code": user.employee_id,
        "height_cm": height,
        "weight_kg": weight,
        "bmi": bmi,
        "bmi_category": get_bmi_category(bmi),
        "age": safe_int(get_val("age", 30)),
        "gender": get_val("gender", "Prefer not to say"),
        "blood_group": get_val("blood_group", "O+"),
        "blood_pressure": get_val("blood_pressure", "120/80"),
        "heart_rate": safe_int(get_val("heart_rate", 72)),
        "blood_sugar": safe_float(get_val("blood_sugar")),
        "cholesterol": safe_float(get_val("cholesterol")),
        "medical_conditions": get_val("medical_conditions"),
        "allergies": get_val("allergies"),
        "current_medications": get_val("current_medications"),
        "disability_status": get_val("disability_status"),
        "smoking_habit": get_val("smoking_habit", "Non-smoker"),
        "alcohol_consumption": get_val("alcohol_consumption", "Never"),
        "daily_water_litres": safe_float(get_val("daily_water_litres", 2.5)),
        "sleep_hours": safe_float(get_val("sleep_hours", 7.0)),
        "exercise_frequency": get_val("exercise_frequency", "3-4 days/week"),
        "exercise_type": get_val("exercise_type", "General Conditioning"),
        "daily_step_count": safe_int(get_val("daily_step_count", 8000)),
        "calories_burned": safe_int(get_val("calories_burned", 2200)),
        "stress_level": get_val("stress_level", "Moderate"),
        "mental_health_score": safe_int(get_val("mental_health_score", 75)),
        "attendance_percentage": safe_float(get_val("attendance_percentage", 95.0)),
        "work_hours_per_day": safe_float(get_val("work_hours_per_day", 8.0)),
        "screen_time": safe_float(get_val("screen_time", 6.0)),
        "health_checkup_date": parse_date(get_val("health_checkup_date")),
        "doctor_remarks": get_val("doctor_remarks"),
    }
    data["wellness_score"] = calculate_wellness_score(
        data["sleep_hours"],
        data["exercise_frequency"],
        data["daily_water_litres"],
        data["attendance_percentage"],
        data["stress_level"],
    )
    data["health_risk_score"] = calculate_health_risk_score(data)
    return data


def create_or_update_record(user, form, record=None):
    data = build_record_data(form, user, record=record)
    if record is None:
        record = EmployeeHealth(**data)
        db.session.add(record)
    else:
        for key, value in data.items():
            setattr(record, key, value)
    db.session.commit()
    return record


def get_employee_record(user):
    return EmployeeHealth.query.filter_by(user_id=user.id).first()


def health_record_query(args):
    query = EmployeeHealth.query.join(User)
    search = args.get("search", "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                User.employee_id.ilike(like),
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.department.ilike(like),
                EmployeeHealth.blood_group.ilike(like),
            )
        )
    if args.get("department"):
        query = query.filter(User.department == args["department"])
    if args.get("gender"):
        query = query.filter(EmployeeHealth.gender == args["gender"])
    if args.get("bmi_category"):
        query = query.filter(EmployeeHealth.bmi_category == args["bmi_category"])
    if args.get("stress_level"):
        query = query.filter(EmployeeHealth.stress_level == args["stress_level"])
    if args.get("attendance_band") == "low":
        query = query.filter(EmployeeHealth.attendance_percentage < 75)
    if args.get("attendance_band") == "good":
        query = query.filter(EmployeeHealth.attendance_percentage >= 75)
    if args.get("risk_band") == "high":
        query = query.filter(EmployeeHealth.health_risk_score >= 60)
    if args.get("risk_band") == "normal":
        query = query.filter(EmployeeHealth.health_risk_score < 60)

    sort = args.get("sort", "updated")
    if sort == "department":
        query = query.order_by(User.department.asc())
    elif sort == "bmi":
        query = query.order_by(EmployeeHealth.bmi.desc())
    elif sort == "risk":
        query = query.order_by(EmployeeHealth.health_risk_score.desc())
    else:
        query = query.order_by(EmployeeHealth.updated_at.desc())
    return query


def dashboard_metrics(records):
    total = len(records)
    if not total:
        return {
            "average_bmi": 0,
            "average_wellness": 0,
            "high_risk": 0,
            "normal_bmi": 0,
            "average_sleep": 0,
            "average_exercise": 0,
            "average_attendance": 0,
        }
    return {
        "average_bmi": round(sum(r.bmi for r in records) / total, 1),
        "average_wellness": round(sum(r.wellness_score for r in records) / total, 1),
        "high_risk": sum(1 for r in records if r.health_risk_score >= 60),
        "normal_bmi": sum(1 for r in records if r.bmi_category == "Normal"),
        "average_sleep": round(sum(r.sleep_hours for r in records) / total, 1),
        "average_exercise": round(sum(_exercise_points(r.exercise_frequency) for r in records) / total, 1),
        "average_attendance": round(sum(r.attendance_percentage for r in records) / total, 1),
    }


def chart_payload(records):
    def counts(attr):
        counter = Counter(getattr(record, attr) for record in records)
        return {"labels": list(counter.keys()), "values": list(counter.values())}

    age_bands = Counter()
    for record in records:
        if record.age < 25:
            age_bands["Under 25"] += 1
        elif record.age <= 35:
            age_bands["25-35"] += 1
        elif record.age <= 45:
            age_bands["36-45"] += 1
        else:
            age_bands["46+"] += 1

    return {
        "bmi": counts("bmi_category"),
        "age": {"labels": list(age_bands.keys()), "values": list(age_bands.values())},
        "sleep": {"labels": [r.user.full_name for r in records], "values": [r.sleep_hours for r in records]},
        "exercise": counts("exercise_frequency"),
        "attendance": {"labels": [r.user.full_name for r in records], "values": [r.attendance_percentage for r in records]},
        "stress": counts("stress_level"),
    }
