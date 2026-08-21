import os
from datetime import timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "EmployeeWellnessAnalytics@2026")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "employee_wellness.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "353002524557-81se2d7858ui05g477g3f9pq6913nfkh" + ".apps.googleusercontent.com")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "GOCSPX-nexaOcKgt4sXDUA5" + "LRqMiG6aRIYe")
    GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://127.0.0.1:5000/login/google/callback")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
