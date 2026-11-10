from flask import Blueprint, jsonify, render_template, request

from app.models import document_metadata as db
from app.routes.auth_routes import current_user, login_required
from app.services import llm_service, rag_service

bp = Blueprint("chat", __name__)
MAX_QUESTION_CHARS = 1000


@bp.route("/")
@login_required
def index():
    return render_template("index.html", user=current_user())


@bp.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    question = str(data.get("message", "")).strip()
    if not question:
        return jsonify({"error": "Please type a question."}), 400
    if len(question) > MAX_QUESTION_CHARS:
        return jsonify({"error": f"Questions are limited to {MAX_QUESTION_CHARS} characters."}), 400

    user = current_user()
    try:
        result = rag_service.answer(question, user, data.get("history"))
    except llm_service.LLMUnavailable as exc:
        return jsonify({"error": str(exc)}), 503
    db.log_question(user["id"], question, result["answered"])
    return jsonify(result)
