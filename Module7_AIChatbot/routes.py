from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from database import db
from Module7_AIChatbot.models import CheckupAppointment, ChatMessage
from Module7_AIChatbot.services import process_chatbot_query

module7_bp = Blueprint("module7", __name__, url_prefix="/chatbot")


@module7_bp.route("/", methods=["GET"])
@login_required
def index():
    messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp.asc()).all()
    appointments = CheckupAppointment.query.filter_by(user_id=current_user.id).order_by(CheckupAppointment.created_at.desc()).all()
    
    return render_template(
        "modules/module7.html",
        messages=messages,
        appointments=appointments
    )


@module7_bp.route("/ask", methods=["POST"])
@login_required
def ask():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Message is required."}), 400
        
    query = data["message"].strip()
    language = data.get("language", "en-US")
    if not query:
        return jsonify({"error": "Message cannot be empty."}), 400
        
    reply = process_chatbot_query(query, current_user, language=language)
    return jsonify({"response": reply})


@module7_bp.route("/clear", methods=["POST"])
@login_required
def clear_chat():
    ChatMessage.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash("Chat history cleared successfully.", "success")
    return redirect(url_for("module7.index"))


@module7_bp.route("/cancel-appointment/<int:id>", methods=["POST"])
@login_required
def cancel_appointment(id):
    appointment = CheckupAppointment.query.get_or_404(id)
    if appointment.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("module7.index"))
        
    db.session.delete(appointment)
    db.session.commit()
    flash("Checkup appointment successfully cancelled.", "success")
    return redirect(url_for("module7.index"))
