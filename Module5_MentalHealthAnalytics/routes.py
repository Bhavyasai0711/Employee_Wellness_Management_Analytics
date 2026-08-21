from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from Module5_MentalHealthAnalytics.models import SentimentLog
from Module5_MentalHealthAnalytics.services import analyze_mental_health_text

module5_bp = Blueprint("module5", __name__, url_prefix="/mental-health-analytics")


@module5_bp.route("/", methods=["GET"])
@login_required
def index():
    user_logs = SentimentLog.query.filter_by(user_id=current_user.id).order_by(SentimentLog.created_at.asc()).all()
    
    timeline_dates = [log.created_at.strftime("%m-%d %H:%M") for log in user_logs]
    timeline_polarity = [log.polarity for log in user_logs]
    
    latest_log = user_logs[-1] if user_logs else None
    
    admin_metrics = {}
    all_logs = []
    if current_user.role == "admin":
        all_logs = SentimentLog.query.order_by(SentimentLog.created_at.desc()).all()
        total_logs = len(all_logs)
        
        burnout_count = sum(1 for l in all_logs if l.stress_category == "Burnout Warning")
        anxiety_count = sum(1 for l in all_logs if l.stress_category == "Anxiety Alert")
        low_mood_count = sum(1 for l in all_logs if l.stress_category == "Low Mood / Stress Warning")
        stable_count = total_logs - (burnout_count + anxiety_count + low_mood_count)
        
        admin_metrics = {
            "total_logs": total_logs,
            "burnout_alerts": burnout_count,
            "anxiety_alerts": anxiety_count,
            "low_mood_alerts": low_mood_count,
            "stable_profiles": stable_count
        }
        
    return render_template(
        "modules/module5.html",
        user_logs=user_logs,
        latest_log=latest_log,
        timeline_dates=timeline_dates,
        timeline_polarity=timeline_polarity,
        all_logs=all_logs,
        admin_metrics=admin_metrics
    )


@module5_bp.route("/checkin", methods=["POST"])
@login_required
def checkin():
    feedback = request.form.get("feedback_text", "").strip()
    if not feedback:
        flash("Check-in text cannot be empty.", "warning")
        return redirect(url_for("module5.index"))
        
    log = analyze_mental_health_text(feedback, current_user)
    
    if log.stress_category == "Burnout Warning":
        flash("AI Audit: Burnout indicators detected. We advise reducing screen time and taking breaks.", "danger")
    elif log.stress_category == "Anxiety Alert":
        flash("AI Audit: Increased anxiety indicators detected. Consider relaxing with deep breathing.", "warning")
    else:
        flash("Daily wellness journal entry successfully logged and parsed by AI!", "success")
        
    return redirect(url_for("module5.index"))
