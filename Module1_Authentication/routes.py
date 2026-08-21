import json
import random
import secrets
import urllib.parse
import urllib.request
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from database import bcrypt, db
from models.password_reset import PasswordReset
from models.user import User
from Module1_Authentication.services import (
    log_login,
    otp_is_valid,
    register_failed_attempt,
    reset_failed_attempts,
    validate_password,
)
from Module2_EmployeeHealthData.models import EmployeeHealth

auth_bp = Blueprint("auth", __name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _google_oauth_configured():
    return bool(current_app.config.get("GOOGLE_CLIENT_ID") and current_app.config.get("GOOGLE_CLIENT_SECRET"))


def _get_google_redirect_uri():
    return current_app.config.get("GOOGLE_REDIRECT_URI") or url_for("auth.google_callback", _external=True)


def _generated_employee_id(email):
    local_part = email.split("@")[0].upper()
    cleaned = "".join(ch for ch in local_part if ch.isalnum())[:10] or "GOOGLE"
    base_id = f"GOOGLE-{cleaned}"
    employee_id = base_id
    counter = 1
    while User.query.filter_by(employee_id=employee_id).first():
        counter += 1
        employee_id = f"{base_id}-{counter}"
    return employee_id


def _create_google_user(profile):
    name_parts = (profile.get("name") or "Google User").strip().split()
    first_name = profile.get("given_name") or name_parts[0]
    last_name = profile.get("family_name") or (" ".join(name_parts[1:]) if len(name_parts) > 1 else "User")
    email = profile["email"].lower()
    user = User(
        first_name=first_name,
        last_name=last_name,
        employee_id=_generated_employee_id(email),
        email=email,
        phone="Not Provided",
        department="General",
        gender="Prefer not to say",
        date_of_birth=User.parse_dob("2000-01-01"),
        role="employee",
    )
    user.set_password(secrets.token_urlsafe(24))
    db.session.add(user)
    db.session.commit()
    return user


@auth_bp.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    return render_template("index.html")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        form = request.form
        password = form.get("password", "")
        confirm_password = form.get("confirm_password", "")
        errors = validate_password(password)

        if password != confirm_password:
            errors.append("Password and confirm password must match")
        if not form.get("terms"):
            errors.append("You must accept the terms and conditions")
        if User.query.filter_by(email=form.get("email", "").lower()).first():
            errors.append("Email is already registered")
        if User.query.filter_by(employee_id=form.get("employee_id", "").upper()).first():
            errors.append("Employee/Admin ID is already registered")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("auth/signup.html", form=form)

        user = User(
            first_name=form["first_name"].strip(),
            last_name=form["last_name"].strip(),
            employee_id=form["employee_id"].strip().upper(),
            email=form["email"].strip().lower(),
            phone=form["phone"].strip(),
            department=form["department"].strip(),
            gender=form["gender"],
            date_of_birth=User.parse_dob(form["date_of_birth"]),
            role=form["role"],
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))
        user = User.query.filter(
            (User.email == identifier.lower()) | (User.employee_id == identifier.upper())
        ).first()

        if not user:
            log_login(identifier, "failed", message="Unknown account")
            flash("Invalid login credentials.", "danger")
            return render_template("auth/login.html")

        if user.is_locked:
            log_login(identifier, "locked", user=user, message="Account locked")
            flash("Account locked after 5 failed attempts. Please reset your password.", "danger")
            return render_template("auth/login.html")

        if not user.check_password(password):
            register_failed_attempt(user)
            log_login(identifier, "failed", user=user, message="Invalid password")
            remaining = max(0, 5 - user.failed_login_attempts)
            flash(f"Invalid login credentials. Attempts remaining: {remaining}", "danger")
            return render_template("auth/login.html")

        reset_failed_attempts(user)
        login_user(user, remember=remember)
        session.permanent = True
        log_login(identifier, "success", user=user, message="Login successful")
        flash(f"Welcome back, {user.first_name}.", "success")
        return redirect(url_for("auth.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/login/google")
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    if not _google_oauth_configured():
        flash("Google login is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET first.", "warning")
        return redirect(url_for("auth.login"))

    state = secrets.token_urlsafe(32)
    session["google_oauth_state"] = state
    params = {
        "client_id": current_app.config["GOOGLE_CLIENT_ID"],
        "redirect_uri": _get_google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return redirect(f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}")


@auth_bp.route("/login/google/callback")
def google_callback():
    if request.args.get("state") != session.pop("google_oauth_state", None):
        flash("Google login session expired. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    code = request.args.get("code")
    if not code:
        flash("Google login was cancelled or failed.", "danger")
        return redirect(url_for("auth.login"))

    token_payload = urllib.parse.urlencode({
        "code": code,
        "client_id": current_app.config["GOOGLE_CLIENT_ID"],
        "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
        "redirect_uri": _get_google_redirect_uri(),
        "grant_type": "authorization_code",
    }).encode("utf-8")

    try:
        token_request = urllib.request.Request(
            GOOGLE_TOKEN_URL,
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(token_request, timeout=10) as response:
            token_data = json.loads(response.read().decode("utf-8"))

        userinfo_request = urllib.request.Request(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        with urllib.request.urlopen(userinfo_request, timeout=10) as response:
            profile = json.loads(response.read().decode("utf-8"))
    except Exception:
        flash("Unable to complete Google login right now. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    if not profile.get("email_verified"):
        flash("Please use a verified Google email address.", "danger")
        return redirect(url_for("auth.login"))

    email = profile["email"].lower()
    user = User.query.filter_by(email=email).first() or _create_google_user(profile)
    if user.is_locked:
        log_login(email, "locked", user=user, message="Google login blocked for locked account")
        flash("Your account is locked. Please reset your password.", "danger")
        return redirect(url_for("auth.login"))

    reset_failed_attempts(user)
    login_user(user, remember=True)
    session.permanent = True
    log_login(email, "success", user=user, message="Google OAuth login successful")
    flash(f"Welcome, {user.first_name}.", "success")
    return redirect(url_for("auth.dashboard"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():

    # Admin Dashboard
    if current_user.role == "admin":
        employee_count = User.query.filter_by(role="employee").count()
        all_users = User.query.filter(User.role != "admin").all()
        from Module2_EmployeeHealthData.models import EmployeeDeletionLog
        deletion_logs = EmployeeDeletionLog.query.order_by(EmployeeDeletionLog.deleted_at.desc()).all()

        return render_template(
            "dashboard/admin_dashboard.html",
            employee_count=employee_count,
            all_users=all_users,
            deletion_logs=deletion_logs
        )

    # Employee Health Record
    health = EmployeeHealth.query.filter_by(
        user_id=current_user.id
    ).first()

    # Wellness Quotes
    wellness_quotes = [
        {
            "quote": "Take care of your body. It's the only place you have to live.",
            "author": "Jim Rohn"
        },
        {
            "quote": "Health is the greatest gift, contentment the greatest wealth.",
            "author": "Buddha"
        },
        {
            "quote": "Every healthy choice today builds a stronger tomorrow.",
            "author": "Employee Wellness"
        },
        {
            "quote": "A healthy employee is a productive employee.",
            "author": "Corporate Wellness"
        },
        {
            "quote": "Small healthy habits lead to big achievements.",
            "author": "Wellness Team"
        },
        {
            "quote": "Your future depends on what you do for your health today.",
            "author": "Mahatma Gandhi"
        },
        {
            "quote": "Wellness is not a destination. It is a daily journey.",
            "author": "Anonymous"
        },
        {
            "quote": "A healthy mind and body are the foundation of success.",
            "author": "Infosys Wellness"
        }
    ]

    daily_quote = random.choice(wellness_quotes)

    return render_template(
        "dashboard/employee_dashboard.html",
        health=health,
        quote=daily_quote
    )

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account found for that email address.", "danger")
            return render_template("auth/forgot_password.html")

        otp = f"{random.randint(100000, 999999)}"
        reset_request = PasswordReset(
            user_id=user.id,
            email=email,
            otp_hash=bcrypt.generate_password_hash(otp).decode("utf-8"),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db.session.add(reset_request)
        db.session.commit()
        session["reset_email"] = email
        session["reset_request_id"] = reset_request.id
        print(f"[DEV OTP] Password reset OTP for {email}: {otp}")
        flash("OTP generated. Check the Flask terminal output for development.", "info")
        return redirect(url_for("auth.verify_otp"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    reset_request = PasswordReset.query.get(session.get("reset_request_id"))
    if not otp_is_valid(reset_request):
        flash("OTP expired or invalid. Please request a new one.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        otp = request.form.get("otp", "")
        if bcrypt.check_password_hash(reset_request.otp_hash, otp):
            session["otp_verified"] = True
            flash("OTP verified. Create your new password.", "success")
            return redirect(url_for("auth.reset_password"))
        flash("Invalid OTP.", "danger")

    return render_template("auth/verify_otp.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if not session.get("otp_verified"):
        return redirect(url_for("auth.forgot_password"))

    reset_request = PasswordReset.query.get(session.get("reset_request_id"))
    if not otp_is_valid(reset_request):
        flash("Reset session expired. Please request a new OTP.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        errors = validate_password(password)
        if password != confirm_password:
            errors.append("Password and confirm password must match")
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("auth/reset_password.html")

        user = User.query.get(reset_request.user_id)
        user.set_password(password)
        user.failed_login_attempts = 0
        user.is_locked = False
        reset_request.is_used = True
        db.session.commit()
        session.pop("reset_email", None)
        session.pop("reset_request_id", None)
        session.pop("otp_verified", None)
        flash("Password reset successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html")


@auth_bp.route("/upload-profile", methods=["GET", "POST"])
@login_required
def upload_profile():

    if request.method == "POST":

        if "profile_image" not in request.files:
            flash("No file selected.", "danger")
            return redirect(url_for("auth.dashboard"))

        file = request.files["profile_image"]

        if file.filename == "":
            flash("No file selected.", "danger")
            return redirect(url_for("auth.dashboard"))

        filename = secure_filename(file.filename)

        upload_folder = os.path.join(
            current_app.root_path,
            "static",
            "uploads",
            "profile_images"
        )

        os.makedirs(upload_folder, exist_ok=True)

        file.save(
            os.path.join(upload_folder, filename)
        )

        current_user.profile_image = filename

        db.session.commit()

        flash("Profile image updated successfully!", "success")

        return redirect(url_for("auth.dashboard"))


    return render_template(
        "auth/upload_profile.html"
    )
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.landing"))
