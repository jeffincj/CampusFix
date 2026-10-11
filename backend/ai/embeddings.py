"""
Embeddings + FAISS duplicate search.

An embedding is a list of numbers that represents the meaning/shape of a text.
Similar complaints have similar vectors; we compare them with cosine similarity
(1.0 = identical direction, 0 = unrelated).

Providers (EMBEDDING_PROVIDER in .env):
- "local" (default): character n-grams hashed into 2048 numbers. Works offline for any
  script (Tamil, Malayalam, English, mixed), costs nothing, and is very good at
  near-duplicates ("wifi not working in B block" vs "Wi-Fi not working B-block").
- "sentence-transformers": a multilingual neural model that also matches paraphrases
  (pip install sentence-transformers; set EMBEDDING_MODEL).

Vectors are stored in the complaints table (embedding column). For each search we build
a FAISS index from the open complaints, which is simple and always up to date.
"""
import os
import re
from datetime import timedelta

import faiss
import numpy as np
from django.db.models import F
from django.utils import timezone
from sklearn.feature_extraction.text import HashingVectorizer

OPEN_STATUSES = ("open", "in_progress")
SEARCH_WINDOW_DAYS = 30


def duplicate_threshold():
    return float(os.getenv("DUPLICATE_THRESHOLD", "0.85"))


def normalise(text):
    """Lowercase, unify common spellings, drop punctuation, squeeze spaces."""
    text = text.lower().replace("wi-fi", "wifi").replace("wi fi", "wifi")
    text = re.sub(r"[^\w\s஀-௿ഀ-ൿ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class LocalEmbedder:
    name = "local-char-2048"
    dim = 2048

    def __init__(self):
        self.vectorizer = HashingVectorizer(
            analyzer="char_wb", ngram_range=(2, 4), n_features=self.dim, alternate_sign=False, norm="l2"
        )

    def embed(self, texts):
        vectors = self.vectorizer.transform([normalise(t) for t in texts]).toarray().astype("float32")
        return vectors  # already L2-normalised, so dot product = cosine similarity


class SentenceTransformerEmbedder:
    def __init__(self):
        from sentence_transformers import SentenceTransformer  # optional, heavy dependency

        model_name = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
        self.model = SentenceTransformer(model_name)
        self.name = f"st-{model_name}"
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, texts):
        return self.model.encode(list(texts), normalize_embeddings=True).astype("float32")


_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        provider = os.getenv("EMBEDDING_PROVIDER", "local")
        _embedder = SentenceTransformerEmbedder() if provider == "sentence-transformers" else LocalEmbedder()
    return _embedder


def embed_text(text):
    """One text -> one float32 vector."""
    return get_embedder().embed([text])[0]


def to_bytes(vector):
    return np.asarray(vector, dtype="float32").tobytes()


def from_bytes(blob):
    return np.frombuffer(bytes(blob), dtype="float32")


def build_index(vectors):
    """FAISS index for cosine similarity (inner product on normalised vectors)."""
    matrix = np.vstack(vectors).astype("float32")
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    return index


def find_duplicate(complaint, vector, threshold=None):
    """
    Search open complaints for the most similar one.
    Rules: same embedding model, created in the last 30 days, and the same block if the
    new complaint has one (the same problem in another building is a different problem).
    Returns (original_complaint, similarity) or None.
    """
    from complaints.models import Complaint

    threshold = duplicate_threshold() if threshold is None else threshold
    candidates = (
        Complaint.objects.filter(status__in=OPEN_STATUSES, embedding_model=get_embedder().name,
                                 created_at__gte=timezone.now() - timedelta(days=SEARCH_WINDOW_DAYS))
        .exclude(pk=complaint.pk)
        .exclude(embedding__isnull=True)
        .only("id", "embedding")
    )
    if complaint.block:
        candidates = candidates.filter(block=complaint.block)
    candidates = list(candidates)
    if not candidates:
        return None

    index = build_index([from_bytes(c.embedding) for c in candidates])
    scores, positions = index.search(np.asarray([vector], dtype="float32"), 1)
    similarity, best = float(scores[0][0]), int(positions[0][0])
    if similarity < threshold:
        return None
    original = Complaint.objects.get(pk=candidates[best].pk)
    # If that complaint is itself a duplicate, link to its original instead (keep one "main" complaint).
    parent_link = original.duplicate_of.select_related("original").first()
    if parent_link:
        original = parent_link.original
    return original, similarity


def link_duplicate(original, duplicate, similarity):
    """Save the link and increase the original's duplicate counter."""
    from complaints.models import Complaint, DuplicateLink

    link, created = DuplicateLink.objects.get_or_create(
        original=original, duplicate=duplicate, defaults={"similarity": round(similarity, 4)}
    )
    if created:
        Complaint.objects.filter(pk=original.pk).update(duplicate_count=F("duplicate_count") + 1)
    return link
