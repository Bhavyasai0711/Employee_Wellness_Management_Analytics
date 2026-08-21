from datetime import datetime
from database import db

class SentimentLog(db.Model):
    __tablename__ = "sentiment_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    feedback_text = db.Column(db.Text, nullable=False)
    polarity = db.Column(db.Float, nullable=False)
    subjectivity = db.Column(db.Float, nullable=False)
    stress_category = db.Column(db.String(50), nullable=False)  # 'Stable', 'Anxiety Alert', 'Burnout Warning'
    sentiment_label = db.Column(db.String(30), nullable=False)  # 'Positive', 'Neutral', 'Negative'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("sentiment_logs", lazy=True, cascade="all, delete-orphan"))
