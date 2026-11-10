import re
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request

from config import Config
from app.models import document_metadata as db
from app.routes.auth_routes import admin_required, current_user
from app.services import document_service
from app.utils.file_validator import validate_upload

bp = Blueprint("documents", __name__)
CATEGORIES = ["leave", "claims", "medical", "general"]


@bp.route("/admin")
@admin_required
def admin_page():
    return render_template("admin.html", user=current_user(), categories=CATEGORIES)


@bp.route("/api/admin/documents", methods=["GET"])
@admin_required
def list_documents():
    return jsonify(db.list_documents())


@bp.route("/api/admin/documents", methods=["POST"])
@admin_required
def upload_document():
    """Upload a new policy. Using an existing name replaces it as a new version."""
    f = request.files.get("file")
    ext, error = validate_upload(f)
    if error:
        return jsonify({"error": error}), 400

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "general")
    if not name:
        return jsonify({"error": "Please enter a policy name."}), 400
    if category not in CATEGORIES:
        return jsonify({"error": "Unknown category."}), 400

    version = db.max_version(name) + 1
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "policy"
    dest_dir = Config.POLICY_DIR / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{slug}_v{version}{ext}"
    f.save(dest)

    try:
        doc = document_service.add_document(
            dest, name, category,
            access_level=request.form.get("access_level", "all").strip() or "all",
            effective_date=request.form.get("effective_date", "").strip(),
            expiry_date=request.form.get("expiry_date", "").strip(),
            uploaded_by=current_user()["email"])
    except ValueError as exc:
        Path(dest).unlink(missing_ok=True)
        return jsonify({"error": str(exc)}), 400
    return jsonify(doc), 201


@bp.route("/api/admin/documents/<int:doc_id>", methods=["DELETE"])
@admin_required
def remove_document(doc_id):
    if not db.get_document(doc_id):
        return jsonify({"error": "Document not found."}), 404
    document_service.remove_document(doc_id)
    return jsonify({"ok": True})


@bp.route("/api/admin/unanswered", methods=["GET"])
@admin_required
def unanswered():
    return jsonify(db.unanswered_questions())
