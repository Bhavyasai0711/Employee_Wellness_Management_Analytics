import re
from datetime import datetime

from flask import request

from database import db
from models.login_history import LoginHistory


PASSWORD_RULES = {
    "length": r".{8,}",
    "upper": r"[A-Z]",
    "lower": r"[a-z]",
    "number": r"\d",
    "special": r"[^A-Za-z0-9]",
}


def validate_password(password):
    errors = []
    labels = {
        "length": "Minimum 8 characters",
        "upper": "One uppercase letter",
        "lower": "One lowercase letter",
        "number": "One number",
        "special": "One special character",
    }
    for key, pattern in PASSWORD_RULES.items():
        if not re.search(pattern, password or ""):
            errors.append(labels[key])
    return errors


def log_login(identifier, status, user=None, message=None):
    entry = LoginHistory(
        user_id=user.id if user else None,
        identifier=identifier,
        role=user.role if user else None,
        status=status,
        message=message,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        user_agent=(request.user_agent.string or "")[:255],
    )
    db.session.add(entry)
    db.session.commit()


def reset_failed_attempts(user):
    user.failed_login_attempts = 0
    user.is_locked = False
    db.session.commit()


def register_failed_attempt(user):
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= 5:
        user.is_locked = True
    db.session.commit()


def otp_is_valid(reset_request):
    return reset_request and not reset_request.is_used and reset_request.expires_at > datetime.utcnow()
