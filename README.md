# HR Policy Assistant (free, local RAG chatbot)

Staff ask questions about leave, claims, medical allowances and other company policies and get an
answer **with the policy clause it came from**. Everything runs on your own machine at no cost.

| Part | Tool |
|---|---|
| Web app | Flask, HTML, CSS, JavaScript |
| Vector database | ChromaDB (local folder) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (local) |
| Language model | Ollama + Qwen (local) |
| Metadata, users, audit | SQLite |

## 1. Install

1. Install Python 3.10+ and [Ollama](https://ollama.com/download).
2. Download the model (about 2.5 GB, one time):
   ```
   ollama pull qwen3:4b-instruct
   ```
   Low on RAM? Use `ollama pull qwen2.5:3b` and set `OLLAMA_MODEL=qwen2.5:3b` in `.env`.
3. Set up the project:
   ```
   python -m venv .venv
   .venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   copy .env.example .env          # Mac/Linux: cp .env.example .env
   ```
   Edit `.env` and set a long random `SECRET_KEY`.

The embedding model downloads from Hugging Face on first use, then works offline.

## 2. Add users and policies

```
python scripts/create_user.py --demo        # hr@company.com / hr12345, staff@company.com / staff12345, contract@company.com / contract12345
python scripts/ingest_documents.py          # indexes data/policies/<category>/*.pdf|docx|txt
```

Three fictional sample policies are included. Replace them with your own files, or upload from the
admin page after signing in as HR. **Change the demo passwords before real use.**

## 3. Run

```
ollama serve        # skip if Ollama is already running in the background
python main.py
```
Open http://127.0.0.1:5000

## How it works

**Indexing (when HR uploads or changes a policy)**
file → extract text → chunk (900 chars, 150 overlap, keeps page + heading) → embed → ChromaDB.
A new upload with the same policy name becomes version N+1; the old version is archived and removed from search.

**Answering (every question)**
1. The user's access levels are worked out from their profile.
2. ChromaDB returns the closest chunks **only from documents that user may see**, then expired,
   not-yet-effective and too-distant (irrelevant) chunks are dropped.
3. If nothing relevant remains, the bot says it could not find the answer. The LLM is not called, so it cannot invent one.
4. Otherwise Qwen answers from the numbered excerpts only and cites them as [1], [2].
5. The app checks the citations, shows the matching policy name, version, section and page, and flags answers it cannot tie to a clause.
6. Unanswered questions are logged and shown to HR as a list of policy gaps.

## Access levels

Set "Who can see it" when uploading:

| Value | Visible to |
|---|---|
| `all` | everyone |
| `permanent` / `contract` | staff of that employment type |
| `grade:G3` | staff whose grade is G3 |
| `hr_only` | HR admins |

## Project layout

```
app/routes/      auth, chat and admin endpoints
app/services/    document, embedding, retrieval, llm, rag
app/models/      SQLite users, policy versions, audit log
data/policies/   leave, claims, medical, general
scripts/         ingest_documents.py, create_user.py
tests/           retrieval tests + golden-answer accuracy tests
```

## Tests

```
pytest                       # retrieval tests always run; answer tests need Ollama running
```
Add your real questions and expected facts to `GOLDEN` in `tests/test_rag.py` whenever policies change.

## Tuning answer quality

- Wrong "not found" answers: raise `MAX_DISTANCE` (for example 0.80) or `TOP_K` in `.env`.
- Off-topic answers getting through: lower `MAX_DISTANCE`.
- Tables or clauses split badly: adjust `CHUNK_SIZE` / `CHUNK_OVERLAP` in `config.py`.
- Scanned PDFs have no text and are rejected. Run OCR first.
- A larger model such as `qwen3:8b` follows instructions better if your machine can run it.

## Before real company use

- Serve over HTTPS behind a reverse proxy (nginx or Caddy); do not expose port 5000 directly.
- Replace demo accounts. For single sign-on, swap `auth_routes.py` for your company's login.
- Back up `data/hr_assistant.db`, `data/chroma_db/` and `data/policies/`.
- Keep real policies out of Git (the `.gitignore` already excludes them) if you publish this repo.
- The assistant gives information only. Disputes and exceptions still go to HR.
