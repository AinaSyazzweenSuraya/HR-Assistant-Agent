from pathlib import Path

from config import Config


def validate_upload(file_storage):
    """Return (extension, error). error is None when the upload looks safe."""
    if not file_storage or not file_storage.filename:
        return None, "No file selected."
    ext = Path(file_storage.filename).suffix.lower()
    if ext not in Config.ALLOWED_EXTENSIONS:
        return None, "Only PDF, DOCX and TXT files are allowed."

    head = file_storage.stream.read(4096)
    file_storage.stream.seek(0)
    if not head:
        return None, "The file is empty."
    if ext == ".pdf" and not head.startswith(b"%PDF"):
        return None, "This file is not a valid PDF."
    if ext == ".docx" and not head.startswith(b"PK"):
        return None, "This file is not a valid DOCX."
    if ext == ".txt":
        try:
            head.decode("utf-8")
        except UnicodeDecodeError:
            return None, "TXT files must be UTF-8 encoded."
    return ext, None
