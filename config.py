import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 15 * 1024 * 1024  # 15 MB uploads

    DB_PATH = BASE_DIR / "data" / "hr_assistant.db"
    CHROMA_DIR = BASE_DIR / "data" / "chroma_db"
    POLICY_DIR = BASE_DIR / "data" / "policies"
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "180"))

    CHUNK_SIZE = 900       # characters
    CHUNK_OVERLAP = 150
    TOP_K = int(os.getenv("TOP_K", "5"))
    MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "0.70"))
