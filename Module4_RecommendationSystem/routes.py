from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from database import db
from models.user import User
from Module2_EmployeeHealthData.services import get_employee_record
from Module4_RecommendationSystem.models import WellnessReminder, NotificationPreference, ConsentRecord
from Module4_RecommendationSystem.services import (
    WellnessPlan,
    get_content_based_recommendations,
    get_collaborative_recommendations,
    generate_qwen_ai_plan,
    get_video_and_animation_recommendations,
    sync_wellness_reminders,
)

module4_bp = Blueprint("module4", __name__, url_prefix="/personalized-recommendations")


@module4_bp.route("/")
@login_required
def index():
    employees = []
    selected_employee = None
    record = None
    content_recs = None
    collaborative_recs = None
    video_recs = None
    ai_plan = None
    
    if current_user.role == "admin":
        employees = User.query.filter_by(role="employee").all()
        employee_id = request.args.get("employee_id")
        if employee_id:
            selected_employee = User.query.get(employee_id)
            if selected_employee:
                record = get_employee_record(selected_employee)
                if not record:
                    flash(f"Employee {selected_employee.full_name} does not have a health record logged yet.", "warning")
    else:
        # Regular employee
        record = get_employee_record(current_user)
        if not record:
            flash("Please log your health record first to access personalized recommendations.", "warning")
            return redirect(url_for("module2.add_record"))
            
    if record:
        content_recs = get_content_based_recommendations(record)
        collaborative_recs = get_collaborative_recommendations(record)
        video_recs = get_video_and_animation_recommendations(record)
        target_uid = selected_employee.id if selected_employee else current_user.id
        ai_plan = WellnessPlan.query.filter_by(user_id=target_uid).first()
    else:
        target_uid = current_user.id
        
    return render_template(
        "modules/module4.html",
        employees=employees,
        selected_employee=selected_employee,
        selected_uid=target_uid,
        record=record,
        fitness_recs=content_recs["fitness"] if content_recs else [],
        diet_recs=content_recs["diet"] if content_recs else [],
        mental_recs=content_recs["mental_wellness"] if content_recs else [],
        yoga_recs=content_recs["yoga"] if content_recs else [],
        collaborative_recs=collaborative_recs if collaborative_recs else [],
        video_recs=video_recs if video_recs else [],
        youtube_recs=content_recs.get("video_recommendations", []) if content_recs else [],
        ai_plan=ai_plan
    )


@module4_bp.route("/generate-ai", methods=["POST"])
@login_required
def generate_ai():
    employee_id = request.args.get("employee_id") or request.form.get("employee_id")
    
    if current_user.role == "admin":
        if not employee_id:
            flash("Please select an employee first.", "warning")
            return redirect(url_for("module4.index"))
        target_user = User.query.get(employee_id)
        if not target_user:
            flash("Selected employee not found.", "danger")
            return redirect(url_for("module4.index"))
    else:
        target_user = current_user
        
    record = get_employee_record(target_user)
    if not record:
        flash(f"Health record not found for {target_user.full_name}.", "warning")
        return redirect(url_for("module4.index"))
        
    # Generate plan
    plan_text = generate_qwen_ai_plan(record)
    
    # Save or update plan in DB
    existing = WellnessPlan.query.filter_by(user_id=target_user.id).first()
    if existing:
        existing.plan_text = plan_text
    else:
        new_plan = WellnessPlan(user_id=target_user.id, plan_text=plan_text)
        db.session.add(new_plan)
        
    db.session.commit()
    flash(f"Personalized Wellness Plan successfully generated for {target_user.full_name}!", "success")
    
    if current_user.role == "admin":
        return redirect(url_for("module4.index", employee_id=target_user.id))
    return redirect(url_for("module4.index"))


@module4_bp.route("/reminders/<int:reminder_id>/read", methods=["POST"])
@login_required
def mark_reminder_read(reminder_id):
    reminder = WellnessReminder.query.get_or_404(reminder_id)
    if reminder.user_id != current_user.id:
        flash("Unauthorized action.", "warning")
        return redirect(request.referrer or url_for("module4.index"))

    reminder.is_read = True
    db.session.commit()
    flash("Notification marked as read.", "success")
    return redirect(request.referrer or url_for("module4.index"))


@module4_bp.route("/reminders/mark-all-read", methods=["POST"])
@login_required
def mark_all_reminders_read():
    reminders = WellnessReminder.query.filter_by(user_id=current_user.id, is_active=True, is_read=False).all()
    for r in reminders:
        r.is_read = True
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(request.referrer or url_for("module4.index"))


@module4_bp.route("/preferences", methods=["POST"])
@login_required
def update_preferences():
    preferences = NotificationPreference.query.filter_by(user_id=current_user.id).first()
    if preferences is None:
        preferences = NotificationPreference(user_id=current_user.id)
        db.session.add(preferences)
    preferences.reminders_enabled = bool(request.form.get("reminders_enabled"))
    preferences.email_enabled = bool(request.form.get("email_enabled"))
    preferences.weekly_digest = bool(request.form.get("weekly_digest"))
    db.session.commit()
    flash("Notification preferences updated.", "success")
    return redirect(request.referrer or url_for("module4.index"))


@module4_bp.route("/consent", methods=["POST"])
@login_required
def update_consent():
    consent_type = request.form.get("consent_type", "wellness_analysis")
    consent = ConsentRecord.query.filter_by(user_id=current_user.id, consent_type=consent_type).first()
    if consent is None:
        consent = ConsentRecord(user_id=current_user.id, consent_type=consent_type)
        db.session.add(consent)
    consent.granted = bool(request.form.get("granted"))
    db.session.commit()
    flash("Privacy consent updated.", "success")
    return redirect(request.referrer or url_for("module4.index"))
