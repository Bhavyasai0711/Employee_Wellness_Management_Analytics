from flask import Flask
from flask_login import LoginManager

from config import Config
from database import bcrypt, db
from models.user import User

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    from Module1_Authentication.routes import auth_bp
    from Module2_EmployeeHealthData.routes import module2_bp
    from Module3_WellnessRiskPrediction.routes import module3_bp
    from Module4_RecommendationSystem.routes import module4_bp
    from Module5_MentalHealthAnalytics.routes import module5_bp
    from Module6_DashboardAnalytics.routes import module6_bp
    from Module7_AIChatbot.routes import module7_bp
    from Module8_Challenges.routes import module8_bp
    from Module9_GoalsAndAchievements.routes import module9_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(module2_bp)
    app.register_blueprint(module3_bp)
    app.register_blueprint(module4_bp)
    app.register_blueprint(module5_bp)
    app.register_blueprint(module6_bp)
    app.register_blueprint(module7_bp)
    app.register_blueprint(module8_bp)
    app.register_blueprint(module9_bp)

    @app.context_processor
    def inject_notifications():
        from flask_login import current_user
        if current_user.is_authenticated:
            try:
                from Module4_RecommendationSystem.models import WellnessReminder
                from Module2_EmployeeHealthData.services import get_employee_record
                record = get_employee_record(current_user)
                if record:
                    from Module4_RecommendationSystem.services import sync_wellness_reminders
                    sync_wellness_reminders(record)
                unread = WellnessReminder.query.filter_by(user_id=current_user.id, is_active=True, is_read=False).order_by(WellnessReminder.created_at.desc()).all()
                all_reminders = WellnessReminder.query.filter_by(user_id=current_user.id, is_active=True).order_by(WellnessReminder.created_at.desc()).all()
                return dict(unread_notifications=unread, all_notifications=all_reminders)
            except Exception:
                return dict(unread_notifications=[], all_notifications=[])
        return dict(unread_notifications=[], all_notifications=[])

    with app.app_context():
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
