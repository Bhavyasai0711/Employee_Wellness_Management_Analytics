from datetime import datetime
from database import db

class WellnessGoal(db.Model):
    __tablename__ = "wellness_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    metric = db.Column(db.String(40), nullable=False)
    target_value = db.Column(db.Float, nullable=False)
    current_value = db.Column(db.Float, nullable=False, default=0)
    unit = db.Column(db.String(30), nullable=False, default="")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("wellness_goals", lazy=True, cascade="all, delete-orphan"))

    @property
    def progress_percent(self):
        if self.target_value <= 0:
            return 0
        return round(min(100, max(0, self.current_value / self.target_value * 100)), 1)

    @property
    def is_completed(self):
        return self.current_value >= self.target_value
