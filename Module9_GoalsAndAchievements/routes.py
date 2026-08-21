from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from database import db
from models.user import User
from Module2_EmployeeHealthData.services import get_employee_record
from Module9_GoalsAndAchievements.models import WellnessGoal
from Module9_GoalsAndAchievements.services import calculate_user_achievements

module9_bp = Blueprint("module9", __name__, url_prefix="/goals-achievements")


@module9_bp.route("/")
@module9_bp.route("/goals-profile")
@login_required
def index():
    employees = []
    selected_employee = None
    record = None

    if current_user.role == "admin":
        employees = User.query.filter_by(role="employee").all()
        employee_id = request.args.get("employee_id")
        if employee_id:
            selected_employee = User.query.get(employee_id)
            if selected_employee:
                record = get_employee_record(selected_employee)
        if not selected_employee:
            selected_employee = current_user
            record = get_employee_record(current_user)
    else:
        selected_employee = current_user
        record = get_employee_record(current_user)

    goals = WellnessGoal.query.filter_by(user_id=selected_employee.id, is_active=True).order_by(WellnessGoal.created_at.desc()).all() if selected_employee else []
    achievements = calculate_user_achievements(record)

    return render_template(
        "modules/goals_profile.html",
        employees=employees,
        selected_employee=selected_employee,
        record=record,
        goals=goals,
        achievements=achievements
    )


@module9_bp.route("/goals", methods=["POST"])
@login_required
def create_goal():
    title = request.form.get("title", "").strip()
    metric = request.form.get("metric", "steps")
    unit = request.form.get("unit", "").strip()
    try:
        target_value = float(request.form.get("target_value", "0"))
    except ValueError:
        target_value = 0

    if not title or target_value <= 0:
        flash("Goal title and a positive target value are required.", "danger")
        return redirect(url_for("module9.index"))

    goal = WellnessGoal(
        user_id=current_user.id,
        title=title,
        metric=metric,
        target_value=target_value,
        current_value=0,
        unit=unit,
        is_active=True
    )
    db.session.add(goal)
    db.session.commit()
    flash(f"Personal Goal '{title}' created successfully!", "success")
    return redirect(url_for("module9.index"))


@module9_bp.route("/goals/<int:goal_id>/progress", methods=["POST"])
@login_required
def update_goal_progress(goal_id):
    goal = WellnessGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        flash("You can only update your own goals.", "warning")
        return redirect(url_for("module9.index"))
    try:
        current_value = float(request.form.get("current_value", "0"))
    except ValueError:
        flash("Progress must be a valid number.", "danger")
        return redirect(url_for("module9.index"))
    if current_value < 0:
        flash("Progress cannot be negative.", "danger")
        return redirect(url_for("module9.index"))
    goal.current_value = min(current_value, goal.target_value)
    db.session.commit()
    flash("Goal progress updated successfully!", "success")
    return redirect(url_for("module9.index"))


@module9_bp.route("/goals/<int:goal_id>/delete", methods=["POST"])
@login_required
def delete_goal(goal_id):
    goal = WellnessGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        flash("You can only delete your own goals.", "warning")
        return redirect(url_for("module9.index"))
    goal.is_active = False
    db.session.commit()
    flash("Goal archived.", "success")
    return redirect(url_for("module9.index"))
