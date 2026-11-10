"""Local, free embeddings via sentence-transformers (model downloads once, then runs offline)."""
from config import Config

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(Config.EMBEDDING_MODEL)
    return _model


def embed_texts(texts):
    vectors = _get_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def embed_query(text):
    return embed_texts([text])[0]
