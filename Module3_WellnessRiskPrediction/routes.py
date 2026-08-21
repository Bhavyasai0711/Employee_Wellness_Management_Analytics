from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from Module2_EmployeeHealthData.services import get_employee_record
from Module2_EmployeeHealthData.models import EmployeeHealth
from models.user import User
from Module3_WellnessRiskPrediction.services import (
    get_model_cache,
    predict_employee_risk,
    train_and_evaluate_models,
)

module3_bp = Blueprint("module3", __name__, url_prefix="/wellness-risk-prediction")


@module3_bp.route("/", methods=["GET"])
@login_required
def index():
    model_type = request.args.get("model", "XGBoost")
    cache = get_model_cache()
    metrics = cache.get("metrics", {})
    feature_importances = cache.get("feature_importances", {}).get(model_type, {})
    
    # 1. Prediction for logged-in employee (if they have a health record)
    employee_record = get_employee_record(current_user)
    personal_prediction = None
    if employee_record:
        risk_class, prob = predict_employee_risk(employee_record, model_type)
        personal_prediction = {
            "record": employee_record,
            "risk_class": risk_class,
            "probability": prob
        }
        
    # 2. Prediction list for all employees (for admin view)
    all_predictions = []
    if current_user.role == "admin":
        records = EmployeeHealth.query.all()
        for r in records:
            risk_class, prob = predict_employee_risk(r, model_type)
            all_predictions.append({
                "record": r,
                "user": r.user,
                "risk_class": risk_class,
                "probability": prob
            })
            
    # Chart format importances
    chart_labels = list(feature_importances.keys())
    chart_values = list(feature_importances.values())
    
    # Clean label formatting (e.g. daily_water_litres -> Daily Water Litres)
    clean_labels = [label.replace("_", " ").title() for label in chart_labels]
    
    return render_template(
        "modules/module3.html",
        metrics=metrics,
        model_type=model_type,
        personal_prediction=personal_prediction,
        all_predictions=all_predictions,
        chart_labels=clean_labels,
        chart_values=chart_values
    )


@module3_bp.route("/retrain", methods=["POST"])
@login_required
def retrain():
    train_and_evaluate_models()
    flash("Successfully retrained and re-evaluated all Wellness Risk classification models!", "success")
    return redirect(url_for("module3.index"))
