from datetime import datetime

from database import db


class LoginHistory(db.Model):
    __tablename__ = "login_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    identifier = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String(180), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
