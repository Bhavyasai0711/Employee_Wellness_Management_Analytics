import re

from Module2_EmployeeHealthData.models import EmployeeHealth


BP_PATTERN = re.compile(r"^\d{2,3}/\d{2,3}$")


def _float(form, key, default=None):
    value = form.get(key)
    if value in (None, ""):
        return default
    return float(value)


def _int(form, key, default=None):
    value = form.get(key)
    if value in (None, ""):
        return default
    return int(value)


def validate_health_form(form, user, record_id=None):
    errors = []
    required = [
        "height_cm",
        "weight_kg",
        "age",
        "gender",
        "blood_group",
        "blood_pressure",
        "heart_rate",
        "daily_water_litres",
        "sleep_hours",
        "exercise_frequency",
        "stress_level",
        "attendance_percentage",
    ]
    for field in required:
        if not form.get(field):
            errors.append(f"{field.replace('_', ' ').title()} is required")

    try:
        height = _float(form, "height_cm")
        weight = _float(form, "weight_kg")
        sleep = _float(form, "sleep_hours")
        water = _float(form, "daily_water_litres")
        attendance = _float(form, "attendance_percentage")
        heart_rate = _int(form, "heart_rate")
    except ValueError:
        return ["Numeric fields must contain valid numbers"]

    if height is not None and not 50 <= height <= 250:
        errors.append("Height must be between 50 and 250 cm")
    if weight is not None and not 20 <= weight <= 250:
        errors.append("Weight must be between 20 and 250 kg")
    if sleep is not None and not 0 <= sleep <= 24:
        errors.append("Sleep hours must be between 0 and 24")
    if water is not None and not 0 <= water <= 10:
        errors.append("Daily water intake must be between 0 and 10 litres")
    if attendance is not None and not 0 <= attendance <= 100:
        errors.append("Attendance percentage must be between 0 and 100")
    if heart_rate is not None and not 30 <= heart_rate <= 220:
        errors.append("Heart rate must be between 30 and 220 bpm")
    if form.get("blood_pressure") and not BP_PATTERN.match(form["blood_pressure"]):
        errors.append("Blood pressure must use SYS/DIA format, for example 120/80")

    duplicate = EmployeeHealth.query.filter_by(user_id=user.id).first()
    if duplicate and duplicate.id != record_id:
        errors.append("Duplicate health record detected for this employee")

    for key, value in form.items():
        if key.endswith("_csrf"):
            continue
        if isinstance(value, str) and value.strip().startswith("-"):
            errors.append("Negative values are not allowed")
            break

    return errors


def ai_validation_warnings(form):
    warnings = []
    height = _float(form, "height_cm", 0)
    weight = _float(form, "weight_kg", 0)
    sleep = _float(form, "sleep_hours", 0)
    
    # 1. Rule-based Expert Outliers
    if height and (height < 90 or height > 220):
        warnings.append({
            "field": "height_cm",
            "val": str(height),
            "desc": "Height is unusual (< 90cm or > 220cm)."
        })
    if weight and (weight < 35 or weight > 180):
        warnings.append({
            "field": "weight_kg",
            "val": str(weight),
            "desc": "Weight is unusual (< 35kg or > 180kg)."
        })
    if sleep and sleep < 3:
        warnings.append({
            "field": "sleep_hours",
            "val": str(sleep),
            "desc": "Very low sleep hours (< 3 hours)."
        })

    # 2. Scikit-Learn IsolationForest Outlier Model
    try:
        from sklearn.ensemble import IsolationForest
        import numpy as np
        
        records = EmployeeHealth.query.all()
        # Need at least 5 profiles to fit a statistical boundary
        if len(records) >= 5:
            X = []
            for r in records:
                X.append([r.height_cm, r.weight_kg, r.sleep_hours, r.heart_rate, r.attendance_percentage])
            X = np.array(X)
            
            clf = IsolationForest(contamination=0.15, random_state=42)
            clf.fit(X)
            
            current_x = np.array([[
                _float(form, "height_cm", 170),
                _float(form, "weight_kg", 70),
                _float(form, "sleep_hours", 7),
                _int(form, "heart_rate", 72),
                _float(form, "attendance_percentage", 95)
            ]])
            
            pred = clf.predict(current_x)
            if pred[0] == -1:
                warnings.append({
                    "field": "overall_profile",
                    "val": f"H:{current_x[0][0]} W:{current_x[0][1]} S:{current_x[0][2]} HR:{current_x[0][3]}",
                    "desc": "Isolation Forest ML Model: Multi-variable biometric combination flagged as outlier."
                })
    except Exception as e:
        print("ML Outlier warning bypassed:", e)

    return warnings
