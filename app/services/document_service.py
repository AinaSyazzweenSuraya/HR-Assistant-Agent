"""Load PDF/DOCX/TXT files, split into chunks, and manage document versions."""
import re
from datetime import date
from pathlib import Path

from config import Config
from app.models import document_metadata as db
from app.services import retrieval_service

HEADING_RE = re.compile(r"^(\d+(\.\d+)*[.)]?\s+\S.*|[A-Z][A-Z0-9 \-&/]{4,}|#{1,4}\s+.+)$")


# ---- text extraction -------------------------------------------------------
def extract_pages(path):
    """Return a list of (page_number, text)."""
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    if ext == ".docx":
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        doc = Document(str(path))
        lines = []
        for child in doc.element.body.iterchildren():  # keeps paragraphs and tables in order
            if child.tag.endswith("}p"):
                lines.append(Paragraph(child, doc).text)
            elif child.tag.endswith("}tbl"):
                for row in Table(child, doc).rows:
                    lines.append(" | ".join(cell.text.strip() for cell in row.cells))
        return [(1, "\n".join(lines))]
    if ext in (".txt", ".md"):
        return [(1, Path(path).read_text(encoding="utf-8", errors="ignore"))]
    raise ValueError(f"Unsupported file type: {ext}")


def is_heading(line):
    return len(line) <= 90 and not line.endswith(".") and bool(HEADING_RE.match(line))


def chunk_pages(pages, size=None, overlap=None):
    """Split pages into overlapping chunks, remembering page number and nearest heading."""
    size = size or Config.CHUNK_SIZE
    overlap = Config.CHUNK_OVERLAP if overlap is None else overlap
    chunks, section = [], ""
    for page_no, text in pages:
        buf, buf_section = "", section
        for line in (l.strip() for l in text.splitlines()):
            if not line:
                continue
            if is_heading(line):
                if len(buf) >= 150:  # start a new chunk at each section so clauses stay together
                    chunks.append({"text": buf.strip(), "page": page_no, "section": buf_section})
                    buf = ""
                section = line.lstrip("# ").strip()[:100]
            if buf and len(buf) + len(line) + 1 > size:
                chunks.append({"text": buf.strip(), "page": page_no, "section": buf_section})
                buf = buf[-overlap:] if overlap else ""
                buf_section = section
            if not buf:
                buf_section = section
            buf += line + "\n"
            if is_heading(line):
                buf_section = section  # label a chunk with the latest heading it contains
        if buf.strip():
            chunks.append({"text": buf.strip(), "page": page_no, "section": buf_section})
    return chunks


# ---- version management ----------------------------------------------------
def _check_date(value, label):
    if value:
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError(f"{label} must be in YYYY-MM-DD format.")
    return value or ""


def add_document(file_path, name, category, access_level="all",
                 effective_date="", expiry_date="", uploaded_by="system"):
    """Index a new document. If `name` already exists, this becomes the next version
    and the previous version is archived and removed from the search index."""
    effective_date = _check_date(effective_date, "Effective date") or date.today().isoformat()
    expiry_date = _check_date(expiry_date, "Expiry date")

    chunks = chunk_pages(extract_pages(file_path))
    if not chunks:
        raise ValueError("No readable text found. Scanned PDFs need OCR before upload.")

    previous = db.latest_active(name)
    version = db.max_version(name) + 1
    doc_id = db.insert_document(name, category, version, effective_date, expiry_date,
                                str(file_path), uploaded_by, access_level or "all")
    doc = db.get_document(doc_id)
    try:
        retrieval_service.index_chunks(doc, chunks)
    except Exception:
        db.delete_document_row(doc_id)
        raise
    db.set_chunk_count(doc_id, len(chunks))
    if previous:
        db.archive_document(previous["id"])
        retrieval_service.delete_chunks(previous["id"])
    return db.get_document(doc_id)


def remove_document(doc_id):
    retrieval_service.delete_chunks(doc_id)
    db.archive_document(doc_id)


def ingest_folder(root=None, force=False):
    """Index every file under data/policies/<category>/ (folder name = category)."""
    root = Path(root or Config.POLICY_DIR)
    results = []
    for path in sorted(root.glob("*/*")):
        if not path.is_file() or path.suffix.lower() not in Config.ALLOWED_EXTENSIONS:
            continue
        name = path.stem.replace("_", " ").title()
        existing = db.latest_active(name)
        if existing and existing["file_path"] == str(path) and not force:
            results.append((name, "skipped (already indexed)"))
            continue
        doc = add_document(path, name, path.parent.name)
        results.append((name, f"indexed v{doc['version']} ({doc['chunk_count']} chunks)"))
    return results
