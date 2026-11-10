"""End-to-end accuracy checks. Needs Ollama running with the configured model.

Each case lists facts that MUST appear in the answer. Add your own real questions
as your policies grow; this is your regression suite for answer quality.
"""
import pytest
import requests

from config import Config
from app.services import rag_service
from tests.conftest import CONTRACT, PERMANENT


def _ollama_up():
    try:
        return requests.get(Config.OLLAMA_URL, timeout=2).ok
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(not _ollama_up(), reason="Ollama is not running")


def _norm(s):
    return s.lower().replace(" ", "").replace(",", "")


GOLDEN = [
    (PERMANENT, "How many days of annual leave does a permanent employee with 3 years of service get?", ["18"]),
    (CONTRACT, "How many days of annual leave do I get?", ["10"]),
    (PERMANENT, "What is the maximum hotel rate per night?", ["rm250"]),
    (PERMANENT, "How much outpatient medical can I claim a year?", ["rm1000"]),
    (CONTRACT, "How much outpatient medical can I claim a year?", ["rm500"]),
    (PERMANENT, "Within how many days must I submit a travel claim?", ["30"]),
]


@pytest.mark.parametrize("user,question,expected", GOLDEN)
def test_answers_contain_expected_facts(indexed, user, question, expected):
    result = rag_service.answer(question, user)
    assert result["answered"], result["answer"]
    for fact in expected:
        assert fact in _norm(result["answer"]), f"'{fact}' missing in: {result['answer']}"
    assert result["sources"], "answer must cite at least one source"


def test_unknown_topic_is_refused(indexed):
    result = rag_service.answer("What is the CEO's monthly salary?", PERMANENT)
    assert result["answered"] is False
