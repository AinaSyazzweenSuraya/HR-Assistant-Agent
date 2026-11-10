"""SQLite storage for users, policy document metadata and chat audit log.

ChromaDB handles semantic search; this database is the source of truth for
document versions, approval status, access levels and users.
"""
import sqlite3
from datetime import datetime

from config import Config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'employee',            -- employee | hr_admin
    employment_type TEXT NOT NULL DEFAULT 'permanent', -- permanent | contract
    grade TEXT NOT NULL DEFAULT ''                     -- e.g. G3 (optional)
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    version INTEGER NOT NULL,
    effective_date TEXT NOT NULL DEFAULT '',
    expiry_date TEXT NOT NULL DEFAULT '',
    approval_status TEXT NOT NULL DEFAULT 'approved',  -- approved | archived
    file_path TEXT NOT NULL,
    uploaded_by TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    access_level TEXT NOT NULL DEFAULT 'all',
    chunk_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS chat_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    question TEXT NOT NULL,
    answered INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


def connect():
    Config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(Config.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _run(sql, args=(), fetch=None, commit=False):
    conn = connect()
    try:
        cur = conn.execute(sql, args)
        if commit:
            conn.commit()
        if fetch == "one":
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch == "all":
            return [dict(r) for r in cur.fetchall()]
        return cur.lastrowid
    finally:
        conn.close()


def init_db():
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ---- users -----------------------------------------------------------------
def create_user(email, name, password_hash, role="employee", employment_type="permanent", grade=""):
    return _run(
        "INSERT INTO users (email, name, password_hash, role, employment_type, grade) VALUES (?,?,?,?,?,?)",
        (email.lower().strip(), name, password_hash, role, employment_type, grade),
        commit=True,
    )


def get_user_by_email(email):
    return _run("SELECT * FROM users WHERE email = ?", (email.lower().strip(),), fetch="one")


def get_user(user_id):
    return _run("SELECT * FROM users WHERE id = ?", (user_id,), fetch="one")


# ---- documents -------------------------------------------------------------
def insert_document(name, category, version, effective_date, expiry_date,
                    file_path, uploaded_by, access_level):
    return _run(
        """INSERT INTO documents (name, category, version, effective_date, expiry_date,
           approval_status, file_path, uploaded_by, uploaded_at, access_level)
           VALUES (?,?,?,?,?,'approved',?,?,?,?)""",
        (name, category, version, effective_date, expiry_date, file_path,
         uploaded_by, datetime.now().isoformat(timespec="seconds"), access_level),
        commit=True,
    )


def get_document(doc_id):
    return _run("SELECT * FROM documents WHERE id = ?", (doc_id,), fetch="one")


def list_documents(include_archived=False):
    sql = "SELECT * FROM documents"
    if not include_archived:
        sql += " WHERE approval_status = 'approved'"
    return _run(sql + " ORDER BY category, name, version DESC", fetch="all")


def latest_active(name):
    return _run(
        "SELECT * FROM documents WHERE name = ? AND approval_status = 'approved' ORDER BY version DESC",
        (name,), fetch="one")


def max_version(name):
    row = _run("SELECT MAX(version) AS v FROM documents WHERE name = ?", (name,), fetch="one")
    return row["v"] or 0


def archive_document(doc_id):
    _run("UPDATE documents SET approval_status = 'archived' WHERE id = ?", (doc_id,), commit=True)


def delete_document_row(doc_id):
    _run("DELETE FROM documents WHERE id = ?", (doc_id,), commit=True)


def set_chunk_count(doc_id, count):
    _run("UPDATE documents SET chunk_count = ? WHERE id = ?", (count, doc_id), commit=True)


# ---- chat audit ------------------------------------------------------------
def log_question(user_id, question, answered):
    _run("INSERT INTO chat_logs (user_id, question, answered, created_at) VALUES (?,?,?,?)",
         (user_id, question[:500], int(answered), datetime.now().isoformat(timespec="seconds")),
         commit=True)


def unanswered_questions(limit=25):
    return _run(
        "SELECT question, created_at FROM chat_logs WHERE answered = 0 ORDER BY id DESC LIMIT ?",
        (limit,), fetch="all")
