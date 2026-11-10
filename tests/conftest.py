import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Config  # noqa: E402
from app.models import document_metadata as db  # noqa: E402
from app.services import document_service  # noqa: E402

PERMANENT = {"id": 1, "role": "employee", "employment_type": "permanent", "grade": ""}
CONTRACT = {"id": 2, "role": "employee", "employment_type": "contract", "grade": ""}
HR_ADMIN = {"id": 3, "role": "hr_admin", "employment_type": "permanent", "grade": ""}


@pytest.fixture(scope="session")
def indexed(tmp_path_factory):
    """Index the sample policies into a throw-away database and vector store."""
    tmp = tmp_path_factory.mktemp("hr")
    policy_dir = Config.POLICY_DIR  # read sample files from the real folder
    mp = pytest.MonkeyPatch()
    mp.setattr(Config, "DB_PATH", tmp / "test.db")
    mp.setattr(Config, "CHROMA_DIR", tmp / "chroma")
    db.init_db()
    document_service.ingest_folder(policy_dir)
    yield tmp
    mp.undo()
