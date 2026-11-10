import time
from functools import wraps

from flask import (Blueprint, g, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash

from app.models import document_metadata as db

bp = Blueprint("auth", __name__)

_failures = {}  # email -> list of timestamps (simple brute-force guard)
MAX_ATTEMPTS, WINDOW = 5, 300


def current_user():
    if "user" not in g:
        uid = session.get("user_id")
        g.user = db.get_user(uid) if uid else None
    return g.user


def _deny(status, message):
    if request.path.startswith("/api/"):
        return jsonify({"error": message}), status
    return redirect(url_for("auth.login"))


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user():
            return _deny(401, "Please sign in.")
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return _deny(401, "Please sign in.")
        if user["role"] != "hr_admin":
            return jsonify({"error": "HR administrator access required."}), 403
        return view(*args, **kwargs)
    return wrapper


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        now = time.time()
        recent = [t for t in _failures.get(email, []) if now - t < WINDOW]
        _failures[email] = recent
        user = db.get_user_by_email(email)
        if len(recent) >= MAX_ATTEMPTS:
            error = "Too many failed attempts. Try again in a few minutes."
        elif user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = user["id"]
            _failures.pop(email, None)
            return redirect(url_for("chat.index"))
        else:
            _failures.setdefault(email, []).append(now)
            error = "Email or password is incorrect."
    return render_template("login.html", error=error)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
