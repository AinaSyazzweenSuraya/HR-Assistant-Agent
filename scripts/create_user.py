"""Create users.

    python scripts/create_user.py --demo
    python scripts/create_user.py --email ali@company.com --name "Ali" --password S3cret! \
        --role employee --type permanent --grade G3
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from werkzeug.security import generate_password_hash  # noqa: E402

from app.models import document_metadata as db  # noqa: E402

DEMO = [
    ("hr@company.com", "HR Admin", "hr12345", "hr_admin", "permanent", ""),
    ("staff@company.com", "Aina Syazzween", "staff12345", "employee", "permanent", "G3"),
    ("contract@company.com", "Muhd Hafiz", "contract12345", "employee", "contract", ""),
]


def add(email, name, password, role, etype, grade):
    if db.get_user_by_email(email):
        print(f"exists: {email}")
        return
    db.create_user(email, name, generate_password_hash(password), role, etype, grade)
    print(f"created: {email} ({role}, {etype})")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true", help="create 3 demo accounts")
    p.add_argument("--email"); p.add_argument("--name"); p.add_argument("--password")
    p.add_argument("--role", default="employee", choices=["employee", "hr_admin"])
    p.add_argument("--type", default="permanent", choices=["permanent", "contract"])
    p.add_argument("--grade", default="")
    a = p.parse_args()
    db.init_db()
    if a.demo:
        for row in DEMO:
            add(*row)
    elif a.email and a.name and a.password:
        add(a.email, a.name, a.password, a.role, a.type, a.grade)
    else:
        p.error("use --demo or provide --email, --name and --password")


if __name__ == "__main__":
    main()
