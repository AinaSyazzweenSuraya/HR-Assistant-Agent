from app.services import retrieval_service
from app.services.document_service import chunk_pages
from tests.conftest import CONTRACT, HR_ADMIN, PERMANENT


def test_chunker_keeps_section_and_page():
    pages = [(1, "1. Purpose\nSome text.\n2. Hotel limit\nRM250 per night.")]
    chunks = chunk_pages(pages, size=40, overlap=0)
    assert chunks and all(c["page"] == 1 for c in chunks)
    assert any("Hotel" in c["section"] for c in chunks)


def test_leave_question_finds_leave_policy(indexed):
    hits = retrieval_service.search("How many days of annual leave do I get?", PERMANENT)
    assert hits and hits[0]["doc_name"] == "Annual Leave Policy"


def test_claim_question_finds_travel_policy(indexed):
    hits = retrieval_service.search("What is the hotel limit when travelling?", PERMANENT)
    assert hits and hits[0]["doc_name"] == "Travel Claim Policy"


def test_unrelated_question_returns_nothing(indexed):
    assert retrieval_service.search("What is the capital of France?", PERMANENT) == []


def test_access_level_is_enforced(indexed, tmp_path):
    from app.services import document_service
    secret = tmp_path / "bonus.txt"
    secret.write_text("EXECUTIVE BONUS POOL\nThe executive bonus pool is reserved for directors.", encoding="utf-8")
    document_service.add_document(secret, "Executive Bonus Policy", "general", access_level="hr_only")

    q = "Tell me about the executive bonus pool"
    assert not any(h["doc_name"] == "Executive Bonus Policy" for h in retrieval_service.search(q, CONTRACT))
    assert any(h["doc_name"] == "Executive Bonus Policy" for h in retrieval_service.search(q, HR_ADMIN))


def test_new_version_replaces_old(indexed, tmp_path):
    from app.models import document_metadata as db
    from app.services import document_service
    f = tmp_path / "p.txt"
    f.write_text("PARKING\nParking is RM100 per month.", encoding="utf-8")
    v1 = document_service.add_document(f, "Parking Policy", "general")
    f.write_text("PARKING\nParking is RM150 per month.", encoding="utf-8")
    v2 = document_service.add_document(f, "Parking Policy", "general")
    assert v2["version"] == v1["version"] + 1
    assert db.get_document(v1["id"])["approval_status"] == "archived"
    hits = retrieval_service.search("How much is parking per month?", PERMANENT)
    assert hits and all(h["version"] == 2 for h in hits if h["doc_name"] == "Parking Policy")
