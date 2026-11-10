"""Index every policy file under data/policies/<category>/ into ChromaDB.

    python scripts/ingest_documents.py            # index new files only
    python scripts/ingest_documents.py --force    # re-index everything as a new version
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import document_metadata as db  # noqa: E402
from app.services import document_service  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    db.init_db()
    results = document_service.ingest_folder(force=args.force)
    if not results:
        print("No policy files found in data/policies/<category>/")
    for name, status in results:
        print(f"{name}: {status}")


if __name__ == "__main__":
    main()
