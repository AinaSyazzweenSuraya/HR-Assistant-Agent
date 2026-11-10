"""ChromaDB vector store: index, delete and permission-aware search."""
from datetime import date
from pathlib import Path

from config import Config
from app.services import embedding_service

_client = None
_client_path = None


def get_collection():
    global _client, _client_path
    path = str(Config.CHROMA_DIR)
    if _client is None or _client_path != path:
        import chromadb
        Path(path).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=path)
        _client_path = path
    return _client.get_or_create_collection("hr_policies", metadata={"hnsw:space": "cosine"})


def index_chunks(doc, chunks):
    # Prefix each chunk with document name + section so short clauses keep their context.
    texts = [f"{doc['name']} - {c['section']}\n{c['text']}" for c in chunks]
    get_collection().upsert(
        ids=[f"{doc['id']}-{i}" for i in range(len(chunks))],
        embeddings=embedding_service.embed_texts(texts),
        documents=[c["text"] for c in chunks],
        metadatas=[{
            "document_id": doc["id"], "doc_name": doc["name"], "category": doc["category"],
            "version": doc["version"], "page": c["page"], "section": c["section"],
            "access_level": doc["access_level"],
            "effective_date": doc["effective_date"], "expiry_date": doc["expiry_date"],
        } for c in chunks],
    )


def delete_chunks(doc_id):
    get_collection().delete(where={"document_id": doc_id})


def allowed_levels(user):
    """Which document access levels this user may read."""
    levels = ["all", user["employment_type"]]
    if user.get("grade"):
        levels.append(f"grade:{user['grade']}")
    if user["role"] == "hr_admin":
        levels.append("hr_only")
    return levels


def search(question, user, top_k=None):
    """Return the most relevant chunks the user is ALLOWED to see.
    Permissions are enforced here, before anything reaches the LLM."""
    top_k = top_k or Config.TOP_K
    col = get_collection()
    total = col.count()
    if total == 0:
        return []
    res = col.query(
        query_embeddings=[embedding_service.embed_query(question)],
        n_results=min(total, top_k * 4),
        where={"access_level": {"$in": allowed_levels(user)}},
        include=["documents", "metadatas", "distances"],
    )
    today = date.today().isoformat()
    hits = []
    for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        if dist > Config.MAX_DISTANCE:
            continue
        if meta["effective_date"] and meta["effective_date"] > today:
            continue  # not in force yet
        if meta["expiry_date"] and meta["expiry_date"] < today:
            continue  # expired
        hits.append({"text": text, "distance": dist, **meta})
        if len(hits) == top_k:
            break
    return hits
