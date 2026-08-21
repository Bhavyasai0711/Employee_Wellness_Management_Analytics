from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from database import db
from models.user import User
from Module2_EmployeeHealthData.models import EmployeeHealth
from Module5_MentalHealthAnalytics.models import SentimentLog
from Module8_Challenges.models import Challenge, ChallengeParticipation

module8_bp = Blueprint("module8", __name__, url_prefix="/challenges")


def seed_default_challenges():
    if Challenge.query.first() is None:
        challenges = [
            Challenge(
                title="10,000 Steps Daily Challenge",
                description="Walk at least 10,000 steps in a single day to build cardiovascular endurance and burn active calories.",
                target_metric="steps",
                target_value=10000.0,
                points_reward=50
            ),
            Challenge(
                title="Mindfulness Week",
                description="Log at least 3 emotional journals in the Mental Health logs to practice mental clarity and reduce stress.",
                target_metric="mindfulness",
                target_value=3.0,
                points_reward=100
            ),
            Challenge(
                title="Hydration & Sleep Focus",
                description="Maintain at least 7.5 hours of sleep to support cellular recovery and daily cognitive performance.",
                target_metric="sleep",
                target_value=7.5,
                points_reward=60
            )
        ]
        for c in challenges:
            db.session.add(c)
        db.session.commit()


@module8_bp.route("/", methods=["GET"])
@login_required
def index():
    seed_default_challenges()
    
    # 1. Fetch Challenges
    all_challenges = Challenge.query.all()
    participating_ids = {p.challenge_id: p for p in ChallengeParticipation.query.filter_by(user_id=current_user.id).all()}
    
    # 2. Update Progress Dynamically for joined challenges
    for cid, part in participating_ids.items():
        ch = part.challenge
        if part.status != "completed":
            if ch.target_metric == "steps":
                health_record = EmployeeHealth.query.filter_by(user_id=current_user.id).first()
                progress = health_record.daily_step_count if health_record else 0.0
            elif ch.target_metric == "sleep":
                health_record = EmployeeHealth.query.filter_by(user_id=current_user.id).first()
                progress = health_record.sleep_hours if health_record else 0.0
            elif ch.target_metric == "mindfulness":
                progress = float(SentimentLog.query.filter_by(user_id=current_user.id).count())
            else:
                progress = 0.0
                
            part.current_progress = progress
            if progress >= ch.target_value:
                part.status = "completed"
                flash(f"🎉 Challenge Completed: {ch.title}! You earned {ch.points_reward} points!", "success")
            db.session.commit()

    # 3. Calculate Leaderboard (Aggregate points + steps)
    users = User.query.all()
    leaderboard = []
    for u in users:
        completions = ChallengeParticipation.query.filter_by(user_id=u.id, status="completed").all()
        pts = sum(c.challenge.points_reward for c in completions)
        
        health = EmployeeHealth.query.filter_by(user_id=u.id).first()
        steps = health.daily_step_count if health else 0
        pts += int(steps / 200)
        
        leaderboard.append({
            "name": u.full_name,
            "department": u.department or "General",
            "role": u.role,
            "steps": steps,
            "points": pts
        })
        
    leaderboard = sorted(leaderboard, key=lambda x: x["points"], reverse=True)
    
    return render_template(
        "modules/module8.html",
        challenges=all_challenges,
        participations=participating_ids,
        leaderboard=leaderboard
    )


@module8_bp.route("/join/<int:id>", methods=["POST"])
@login_required
def join_challenge(id):
    existing = ChallengeParticipation.query.filter_by(user_id=current_user.id, challenge_id=id).first()
    if not existing:
        participation = ChallengeParticipation(user_id=current_user.id, challenge_id=id, current_progress=0.0, status="joined")
        db.session.add(participation)
        db.session.commit()
        flash("You have successfully joined the challenge! Complete the targets to claim points.", "success")
    return redirect(url_for("module8.index"))


@module8_bp.route("/create", methods=["POST"])
@login_required
def create_challenge():
    if current_user.role != "admin":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("module8.index"))
        
    title = request.form.get("title")
    description = request.form.get("description")
    target_metric = request.form.get("target_metric")
    target_value = float(request.form.get("target_value", 0))
    points_reward = int(request.form.get("points_reward", 50))
    
    if not title or not description:
        flash("Please fill in all details.", "warning")
        return redirect(url_for("module8.index"))
        
    new_challenge = Challenge(
        title=title,
        description=description,
        target_metric=target_metric,
        target_value=target_value,
        points_reward=points_reward
    )
    db.session.add(new_challenge)
    db.session.commit()
    flash(f"Challenge '{title}' launched successfully!", "success")
    return redirect(url_for("module8.index"))
