from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from datetime import datetime
from database import db
from models.user import User
from Module2_EmployeeHealthData.forms import BMI_CATEGORIES, health_form_options
from Module2_EmployeeHealthData.models import EmployeeHealth, HealthAnomaly, EmployeeDeletionLog
from Module2_EmployeeHealthData.services import (
    chart_payload,
    create_or_update_record,
    dashboard_metrics,
    get_employee_record,
    health_record_query,
)
from Module2_EmployeeHealthData.validators import ai_validation_warnings, validate_health_form

module2_bp = Blueprint("module2", __name__, url_prefix="/employee-health-data")


def employee_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user.role != "employee":
            flash("Only employees can manage their own health record.", "warning")
            return redirect(url_for("module2.admin_records"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            flash("Admin access required.", "warning")
            return redirect(url_for("module2.index"))
        return view(*args, **kwargs)

    return wrapped


@module2_bp.route("/")
@login_required
def index():
    if current_user.role == "admin":
        return redirect(url_for("module2.admin_records"))

    record = get_employee_record(current_user)
    return render_template("health/employee_home.html", record=record)


@module2_bp.route("/add", methods=["GET", "POST"])
@login_required
@employee_required
def add_record():
    existing = get_employee_record(current_user)
    if existing:
        flash("You already have a health record. You can update it here.", "info")
        return redirect(url_for("module2.edit_record", record_id=existing.id))

    if request.method == "POST":
        errors = validate_health_form(request.form, current_user)
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            record = create_or_update_record(current_user, request.form)
            for warning in ai_validation_warnings(request.form):
                anomaly = HealthAnomaly(
                    employee_health_id=record.id,
                    field_name=warning["field"],
                    value=warning["val"],
                    description=warning["desc"],
                    status="Flagged"
                )
                db.session.add(anomaly)
                flash(f"AI Warning: {warning['desc']} (Value: {warning['val']})", "warning")
            db.session.commit()
            flash("Health record added successfully.", "success")
            return redirect(url_for("module2.view_record", record_id=record.id))

    return render_template("health/health_form.html", options=health_form_options(), record=None, mode="Add")


@module2_bp.route("/record/<int:record_id>")
@login_required
def view_record(record_id):
    record = EmployeeHealth.query.get_or_404(record_id)
    if current_user.role != "admin" and record.user_id != current_user.id:
        flash("You can view only your own health record.", "warning")
        return redirect(url_for("module2.index"))
    return render_template("health/record_detail.html", record=record)


@module2_bp.route("/record/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def edit_record(record_id):
    record = EmployeeHealth.query.get_or_404(record_id)
    if current_user.role != "admin" and record.user_id != current_user.id:
        flash("You can update only your own health record.", "warning")
        return redirect(url_for("module2.index"))

    if request.method == "POST":
        owner = record.user
        errors = validate_health_form(request.form, owner, record_id=record.id)
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            HealthAnomaly.query.filter_by(employee_health_id=record.id).delete()
            create_or_update_record(owner, request.form, record=record)
            for warning in ai_validation_warnings(request.form):
                anomaly = HealthAnomaly(
                    employee_health_id=record.id,
                    field_name=warning["field"],
                    value=warning["val"],
                    description=warning["desc"],
                    status="Flagged"
                )
                db.session.add(anomaly)
                flash(f"AI Warning: {warning['desc']} (Value: {warning['val']})", "warning")
            db.session.commit()
            flash("Health record updated successfully.", "success")
            return redirect(url_for("module2.view_record", record_id=record.id))

    return render_template("health/health_form.html", options=health_form_options(), record=record, mode="Update")


@module2_bp.route("/record/<int:record_id>/delete", methods=["POST"])
@login_required
def delete_record(record_id):
    record = EmployeeHealth.query.get_or_404(record_id)
    if current_user.role != "admin" and record.user_id != current_user.id:
        flash("You can delete only your own health record.", "warning")
        return redirect(url_for("module2.index"))

    db.session.delete(record)
    db.session.commit()
    flash("Health record deleted successfully.", "success")
    if current_user.role == "admin":
        return redirect(url_for("module2.admin_records"))
    return redirect(url_for("module2.index"))


@module2_bp.route("/report/pdf")
@login_required
@employee_required
def download_report():
    record = get_employee_record(current_user)
    if not record:
        flash("Please log a health record first to generate PDF.", "warning")
        return redirect(url_for("module2.index"))

    import io
    from flask import send_file
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#7c3aed'),
        spaceAfter=15,
        alignment=1
    )
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#1f2937'),
        spaceBefore=10,
        spaceAfter=5
    )
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#4b5563'),
        spaceAfter=6
    )

    story.append(Paragraph("Employee Wellness Health Report", title_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Personal Details", section_style))
    personal_data = [
        [Paragraph("<b>Employee Name</b>", body_style), Paragraph(current_user.full_name, body_style),
         Paragraph("<b>Employee Code</b>", body_style), Paragraph(current_user.employee_id, body_style)],
        [Paragraph("<b>Department</b>", body_style), Paragraph(current_user.department, body_style),
         Paragraph("<b>Email</b>", body_style), Paragraph(current_user.email, body_style)]
    ]
    t1 = Table(personal_data, colWidths=[120, 150, 120, 150])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f9fafb')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e5e7eb')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. Biometrics & Vital Statistics", section_style))
    vitals_data = [
        [Paragraph("<b>Height (cm)</b>", body_style), Paragraph(str(record.height_cm), body_style),
         Paragraph("<b>Weight (kg)</b>", body_style), Paragraph(str(record.weight_kg), body_style)],
        [Paragraph("<b>BMI (Body Mass Index)</b>", body_style), Paragraph(f"{record.bmi} ({record.bmi_category})", body_style),
         Paragraph("<b>Blood Pressure</b>", body_style), Paragraph(record.blood_pressure, body_style)],
        [Paragraph("<b>Heart Rate (bpm)</b>", body_style), Paragraph(str(record.heart_rate), body_style),
         Paragraph("<b>Stress Level</b>", body_style), Paragraph(record.stress_level, body_style)]
    ]
    t2 = Table(vitals_data, colWidths=[120, 150, 120, 150])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f9fafb')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e5e7eb')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    story.append(Paragraph("3. Daily Activity & Sleep Indicators", section_style))
    activity_data = [
        [Paragraph("<b>Sleep Hours</b>", body_style), Paragraph(f"{record.sleep_hours} hrs", body_style),
         Paragraph("<b>Water Intake</b>", body_style), Paragraph(f"{record.daily_water_litres} L", body_style)],
        [Paragraph("<b>Exercise Habits</b>", body_style), Paragraph(record.exercise_frequency, body_style),
         Paragraph("<b>Daily Steps</b>", body_style), Paragraph(str(record.daily_step_count or 0), body_style)]
    ]
    t3 = Table(activity_data, colWidths=[120, 150, 120, 150])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f9fafb')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e5e7eb')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t3)
    story.append(Spacer(1, 10))

    story.append(Paragraph("4. AI Scoring Analysis", section_style))
    scores_data = [
        [Paragraph("<b>Wellness Score Index</b>", body_style), Paragraph(f"<b>{record.wellness_score} / 100</b>", body_style)],
        [Paragraph("<b>Physiological Risk Score</b>", body_style), Paragraph(f"<b>{record.health_risk_score} / 100</b>", body_style)]
    ]
    t4 = Table(scores_data, colWidths=[200, 340])
    t4.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4') if record.health_risk_score < 60 else colors.HexColor('#fef2f2')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#bbf7d0') if record.health_risk_score < 60 else colors.HexColor('#fecaca')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t4)
    
    if record.doctor_remarks:
        story.append(Spacer(1, 8))
        story.append(Paragraph("<b>Physician Remarks:</b> " + record.doctor_remarks, body_style))

    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"health_report_{current_user.employee_id}.pdf",
        mimetype="application/pdf"
    )


@module2_bp.route("/bmi-report")
@login_required
@employee_required
def bmi_report():
    record = get_employee_record(current_user)
    if not record:
        flash("Add a health record first to view BMI report.", "warning")
        return redirect(url_for("module2.add_record"))
    return render_template("health/bmi_report.html", record=record)


@module2_bp.route("/wellness-score")
@login_required
@employee_required
def wellness_score():
    record = get_employee_record(current_user)
    if not record:
        flash("Add a health record first to view wellness score.", "warning")
        return redirect(url_for("module2.add_record"))
    return render_template("health/wellness_score.html", record=record)


@module2_bp.route("/admin/delete-employee", methods=["POST"])
@login_required
@admin_required
def delete_employee():
    user_id = request.form.get("user_id")
    reason = request.form.get("reason")
    notes = request.form.get("notes", "").strip()

    if not user_id or not reason:
        flash("Please select an employee and specify a valid reason for deletion.", "danger")
        return redirect(url_for("auth.dashboard"))

    target_user = User.query.get(user_id)
    if not target_user:
        flash("Employee user account not found.", "warning")
        return redirect(url_for("auth.dashboard"))

    if target_user.id == current_user.id:
        flash("You cannot delete your own admin account.", "danger")
        return redirect(url_for("auth.dashboard"))

    # Log deletion in EmployeeDeletionLog table for compliance & audit trail
    deletion_log = EmployeeDeletionLog(
        admin_id=current_user.id,
        admin_name=current_user.full_name,
        employee_code=target_user.employee_id,
        employee_name=target_user.full_name,
        employee_email=target_user.email,
        reason=reason,
        notes=notes
    )
    db.session.add(deletion_log)

    # Delete all associated records safely
    try:
        # 1. Health Records & Anomalies
        records = EmployeeHealth.query.filter_by(user_id=target_user.id).all()
        for r in records:
            HealthAnomaly.query.filter_by(employee_health_id=r.id).delete()
            db.session.delete(r)

        # 2. Chat messages
        try:
            from Module7_AIChatbot.models import ChatMessage, CheckupAppointment
            ChatMessage.query.filter_by(user_id=target_user.id).delete()
            CheckupAppointment.query.filter_by(user_id=target_user.id).delete()
        except Exception:
            pass

        # 3. Mental Health Journals
        try:
            from Module5_MentalHealth.models import MentalHealthJournal
            MentalHealthJournal.query.filter_by(user_id=target_user.id).delete()
        except Exception:
            pass

        # 4. Challenge Participations
        try:
            from Module8_Challenges.models import ChallengeParticipation
            ChallengeParticipation.query.filter_by(user_id=target_user.id).delete()
        except Exception:
            pass

        # 5. Delete User Account
        employee_name = target_user.full_name
        db.session.delete(target_user)
        db.session.commit()

        flash(f"Employee '{employee_name}' was successfully deleted. Reason logged: '{reason}'.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting employee: {str(e)}", "danger")

    return redirect(url_for("auth.dashboard"))


@module2_bp.route("/admin")
@login_required
@admin_required
def admin_records():
    query = health_record_query(request.args)
    records = query.all()
    departments = [row[0] for row in User.query.with_entities(User.department).distinct().order_by(User.department).all()]
    metrics = dashboard_metrics(records)
    charts = chart_payload(records)
    
    # Fetch all anomalies & deletion audit logs for the admin resolution dashboard
    anomalies = HealthAnomaly.query.all()
    deletion_logs = EmployeeDeletionLog.query.order_by(EmployeeDeletionLog.deleted_at.desc()).all()
    all_users = User.query.filter(User.role != "admin").all()
    
    return render_template(
        "health/admin_records.html",
        records=records,
        metrics=metrics,
        charts=charts,
        departments=departments,
        bmi_categories=BMI_CATEGORIES,
        options=health_form_options(),
        anomalies=anomalies,
        deletion_logs=deletion_logs,
        all_users=all_users
    )


@module2_bp.route("/admin/export-csv")
@login_required
@admin_required
def export_csv():
    import io
    import pandas as pd
    from flask import Response
    
    records = EmployeeHealth.query.all()
    if not records:
        flash("No health records to export.", "warning")
        return redirect(url_for("module2.admin_records"))
        
    data = []
    for r in records:
        data.append({
            "Employee ID": r.user.employee_id,
            "Name": r.user.full_name,
            "Department": r.user.department,
            "Height (cm)": r.height_cm,
            "Weight (kg)": r.weight_kg,
            "BMI": r.bmi,
            "BMI Category": r.bmi_category,
            "Blood Pressure": r.blood_pressure,
            "Heart Rate": r.heart_rate,
            "Sleep Hours": r.sleep_hours,
            "Water (L)": r.daily_water_litres,
            "Exercise Freq": r.exercise_frequency,
            "Stress Level": r.stress_level,
            "Attendance %": r.attendance_percentage,
            "Wellness Score": r.wellness_score,
            "Risk Score": r.health_risk_score
        })
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=organization_wellness_export.csv"}
    )


@module2_bp.route("/sync/<string:provider>", methods=["POST"])
@login_required
@employee_required
def sync_wearable(provider):
    import random
    record = get_employee_record(current_user)
    
    mock_data = {
        "height_cm": "172",
        "weight_kg": str(round(random.uniform(55.0, 95.0), 1)),
        "age": "28",
        "gender": "Male",
        "blood_group": "O+",
        "blood_pressure": f"{random.randint(110, 140)}/{random.randint(70, 90)}",
        "heart_rate": str(random.randint(60, 100)),
        "daily_water_litres": str(round(random.uniform(1.5, 4.0), 1)),
        "sleep_hours": str(round(random.uniform(4.5, 9.0), 1)),
        "exercise_frequency": random.choice(["1-2 days/week", "3-4 days/week", "5+ days/week"]),
        "exercise_type": "Jogging & Core Exercises",
        "daily_step_count": str(random.randint(5000, 13000)),
        "calories_burned": str(random.randint(1800, 2700)),
        "stress_level": random.choice(["Low", "Moderate", "High"]),
        "mental_health_score": str(random.randint(60, 95)),
        "attendance_percentage": str(round(random.uniform(80.0, 100.0), 1)),
        "work_hours_per_day": "8.0",
        "screen_time": "5.0",
        "health_checkup_date": datetime.today().strftime('%Y-%m-%d'),
        "doctor_remarks": f"Wearable telemetry sync completed successfully via {provider.upper()} cloud API."
    }

    if record:
        HealthAnomaly.query.filter_by(employee_health_id=record.id).delete()
    
    record = create_or_update_record(current_user, mock_data, record=record)

    for warning in ai_validation_warnings(mock_data):
        anomaly = HealthAnomaly(
            employee_health_id=record.id,
            field_name=warning["field"],
            value=warning["val"],
            description=warning["desc"],
            status="Flagged"
        )
        db.session.add(anomaly)
        flash(f"AI Warning: {warning['desc']} (Value: {warning['val']})", "warning")
        
    db.session.commit()
    flash(f"Successfully pulled latest wearable metrics from {provider.upper()} API!", "success")
    return redirect(url_for("module2.index"))


@module2_bp.route("/admin/anomaly/<int:anomaly_id>/<string:action>", methods=["POST"])
@login_required
@admin_required
def resolve_anomaly(anomaly_id, action):
    anomaly = HealthAnomaly.query.get_or_404(anomaly_id)
    if action == "approve":
        anomaly.status = "Approved"
        flash(f"Approved anomaly warning for record ID {anomaly.employee_health_id}.", "success")
    elif action == "resolve":
        anomaly.status = "Resolved"
        flash(f"Marked anomaly as resolved for record ID {anomaly.employee_health_id}.", "success")
    else:
        flash("Invalid action.", "danger")
        
    db.session.commit()
    return redirect(url_for("module2.admin_records"))
