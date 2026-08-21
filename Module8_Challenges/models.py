from datetime import datetime
from database import db

class Challenge(db.Model):
    __tablename__ = "challenges"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    target_metric = db.Column(db.String(50), nullable=False)  # 'steps', 'sleep', 'mindfulness'
    target_value = db.Column(db.Float, nullable=False)
    points_reward = db.Column(db.Integer, default=50)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChallengeParticipation(db.Model):
    __tablename__ = "challenge_participations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False, index=True)
    current_progress = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default="joined")  # 'joined', 'completed'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("participations", lazy=True, cascade="all, delete-orphan"))
    challenge = db.relationship("Challenge", backref=db.backref("participations", lazy=True, cascade="all, delete-orphan"))
