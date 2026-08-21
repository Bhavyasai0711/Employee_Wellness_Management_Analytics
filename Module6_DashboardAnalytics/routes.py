from functools import wraps
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from database import db
from models.user import User
from Module2_EmployeeHealthData.models import EmployeeHealth
from Module2_EmployeeHealthData.services import get_employee_record
from Module5_MentalHealthAnalytics.models import SentimentLog
from Module6_DashboardAnalytics.services import (
    calculate_dashboard_metrics,
    generate_predictive_forecast,
)

module6_bp = Blueprint("module6", __name__, url_prefix="/wellness-analytics")


@module6_bp.route("/")
@login_required
def index():
    employees = []
    selected_employee = None
    personal_record = None
    personal_logs = []
    
    if current_user.role == "admin":
        employees = User.query.filter_by(role="employee").all()
        employee_id = request.args.get("employee_id")
        if employee_id:
            selected_employee = User.query.get(employee_id)
            if selected_employee:
                personal_record = get_employee_record(selected_employee)
                personal_logs = SentimentLog.query.filter_by(user_id=selected_employee.id).order_by(SentimentLog.created_at.asc()).all()
    else:
        # Employees view their own personal analytics
        personal_record = get_employee_record(current_user)
        personal_logs = SentimentLog.query.filter_by(user_id=current_user.id).order_by(SentimentLog.created_at.asc()).all()

    # If displaying personal employee analytics (either direct employee or admin inspecting employee)
    if personal_record or selected_employee or current_user.role == "employee":
        dates = [log.created_at.strftime("%m-%d %H:%M") for log in personal_logs]
        polarities = [log.polarity for log in personal_logs]
        
        wellness_score = personal_record.wellness_score if personal_record else 0.0
        risk_score = personal_record.health_risk_score if personal_record else 0.0
        sleep_hours = personal_record.sleep_hours if personal_record else 0.0
        attendance = personal_record.attendance_percentage if personal_record else 0.0
        water_intake = personal_record.daily_water_litres if personal_record else 0.0
        steps = personal_record.daily_step_count if (personal_record and personal_record.daily_step_count) else 0

        # Calculate organizational averages for comparison
        comp_metrics = calculate_dashboard_metrics()
        
        # Calculate individual sentiment breakdown
        pos_count = sum(1 for p in polarities if p > 0.1)
        neu_count = sum(1 for p in polarities if -0.1 <= p <= 0.1)
        neg_count = sum(1 for p in polarities if p < -0.1)
        sentiment_counts = [pos_count, neu_count, neg_count]

        return render_template(
            "modules/employee_analytics.html",
            employees=employees,
            selected_employee=selected_employee,
            record=personal_record,
            dates=dates,
            polarities=polarities,
            wellness_score=wellness_score,
            risk_score=risk_score,
            sleep_hours=sleep_hours,
            attendance=attendance,
            water_intake=water_intake,
            steps=steps,
            comp_metrics=comp_metrics,
            sentiment_counts=sentiment_counts
        )
        
    # Render main Admin BI dashboard
    metrics = calculate_dashboard_metrics()
    hist_x, hist_y, fore_x, fore_y = generate_predictive_forecast()
    
    # Department averages
    departments = [row[0] for row in User.query.with_entities(User.department).distinct().all()]
    dept_names = []
    dept_wellness = []
    dept_stress = []
    
    for dept in departments:
        if not dept:
            continue
        dept_records = EmployeeHealth.query.join(User).filter(User.department == dept).all()
        if dept_records:
            avg_well = sum(r.wellness_score for r in dept_records) / len(dept_records)
            high_stress_count = sum(1 for r in dept_records if r.stress_level in ("High", "Severe"))
            stress_perc = (high_stress_count / len(dept_records)) * 100
            
            dept_names.append(dept)
            dept_wellness.append(round(avg_well, 1))
            dept_stress.append(round(stress_perc, 1))
            
    # Risk vs Absenteeism correlation points
    records = EmployeeHealth.query.all()
    scatter_points = []
    for r in records:
        scatter_points.append({
            "x": r.health_risk_score,
            "y": round(100 - r.attendance_percentage, 1),
            "label": r.user.full_name
        })
        
    insights = []
    if metrics["absenteeism_rate"] > 15:
        insights.append({
            "type": "danger",
            "message": "Critical: Organization absenteeism is elevated. Health risk correlations indicate lack of regular sleep and high stress are main drivers."
        })
    else:
        insights.append({
            "type": "success",
            "message": "Healthy attendance levels maintained. Current absenteeism rates are well below the corporate 8% threshold."
        })
        
    for i, name in enumerate(dept_names):
        if dept_stress[i] > 40:
            insights.append({
                "type": "warning",
                "message": f"Alert: High stress detected in {name} Department. Consider deploying a mandatory mental wellness yoga schedule."
            })
            
    return render_template(
        "modules/module6.html",
        employees=employees,
        metrics=metrics,
        hist_x=hist_x,
        hist_y=hist_y,
        fore_x=fore_x,
        fore_y=fore_y,
        dept_names=dept_names,
        dept_wellness=dept_wellness,
        dept_stress=dept_stress,
        scatter_points=scatter_points,
        insights=insights
    )
