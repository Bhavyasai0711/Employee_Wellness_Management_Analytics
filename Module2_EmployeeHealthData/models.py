from datetime import datetime

from database import db


class EmployeeHealth(db.Model):
    __tablename__ = "employee_health"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    employee_code = db.Column(db.String(40), nullable=False, index=True)
    height_cm = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    bmi = db.Column(db.Float, nullable=False)
    bmi_category = db.Column(db.String(30), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(30), nullable=False)
    blood_group = db.Column(db.String(10), nullable=False)
    blood_pressure = db.Column(db.String(20), nullable=False)
    heart_rate = db.Column(db.Integer, nullable=False)
    blood_sugar = db.Column(db.Float, nullable=True)
    cholesterol = db.Column(db.Float, nullable=True)
    medical_conditions = db.Column(db.Text, nullable=True)
    allergies = db.Column(db.Text, nullable=True)
    current_medications = db.Column(db.Text, nullable=True)
    disability_status = db.Column(db.String(80), nullable=True)
    smoking_habit = db.Column(db.String(30), nullable=False)
    alcohol_consumption = db.Column(db.String(30), nullable=False)
    daily_water_litres = db.Column(db.Float, nullable=False)
    sleep_hours = db.Column(db.Float, nullable=False)
    exercise_frequency = db.Column(db.String(40), nullable=False)
    exercise_type = db.Column(db.String(80), nullable=True)
    daily_step_count = db.Column(db.Integer, nullable=True)
    calories_burned = db.Column(db.Integer, nullable=True)
    stress_level = db.Column(db.String(30), nullable=False)
    mental_health_score = db.Column(db.Integer, nullable=True)
    attendance_percentage = db.Column(db.Float, nullable=False)
    work_hours_per_day = db.Column(db.Float, nullable=True)
    screen_time = db.Column(db.Float, nullable=True)
    health_checkup_date = db.Column(db.Date, nullable=True)
    doctor_remarks = db.Column(db.Text, nullable=True)
    wellness_score = db.Column(db.Float, nullable=False)
    health_risk_score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("health_records", lazy=True))


class HealthAnomaly(db.Model):
    __tablename__ = "health_anomalies"

    id = db.Column(db.Integer, primary_key=True)
    employee_health_id = db.Column(db.Integer, db.ForeignKey("employee_health.id"), nullable=False, index=True)
    field_name = db.Column(db.String(80), nullable=False)
    value = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Flagged")  # 'Flagged', 'Approved', 'Resolved'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    health_record = db.relationship("EmployeeHealth", backref=db.backref("anomalies", lazy=True, cascade="all, delete-orphan"))


class EmployeeDeletionLog(db.Model):
    __tablename__ = "employee_deletion_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, nullable=False)
    admin_name = db.Column(db.String(100), nullable=False)
    employee_code = db.Column(db.String(50), nullable=False)
    employee_name = db.Column(db.String(100), nullable=False)
    employee_email = db.Column(db.String(120), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    deleted_at = db.Column(db.DateTime, default=datetime.utcnow)
