from datetime import date, datetime

from flask_login import UserMixin

from database import bcrypt, db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    employee_id = db.Column(db.String(40), nullable=False, unique=True, index=True)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    phone = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee")
    password_hash = db.Column(db.String(128), nullable=False)
    profile_image = db.Column(
    db.String(120),
    nullable=False,
    default="default.png"
)
    failed_login_attempts = db.Column(db.Integer, default=0)
    is_locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    login_history = db.relationship("LoginHistory", backref="user", lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @staticmethod
    def parse_dob(value):
        return datetime.strptime(value, "%Y-%m-%d").date() if value else date.today()
