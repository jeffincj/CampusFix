"""
RAG (Retrieval-Augmented Generation) over the college rules PDFs.

Ingest:  PDF -> text per page (pypdf) -> chunks of ~800 characters with overlap
         -> embedding per chunk -> saved in document_chunks.
Search:  embed the question -> FAISS finds the closest chunks (candidates) ->
         re-rank them by embedding score + keyword overlap ("hybrid search") ->
         return them with file name and page number, so every answer can cite its source.
The chat agent calls search() as a tool and writes the answer from these chunks.
"""
import re

import numpy as np
from pypdf import PdfReader

from . import embeddings
from .models import Document, DocumentChunk

CHUNK_SIZE = 500  # characters (small chunks = focused passages = better matches)
CHUNK_OVERLAP = 100  # characters repeated between chunks, so a rule cut in half is still found
MIN_SCORE = 0.25  # below this combined score a chunk is not relevant enough
KEYWORD_WEIGHT = 0.5  # share of the final score that comes from keyword overlap

STOPWORDS = set("""a an the is are was were be been to of in on at for from by with and or not no do does did can
could should would will what when where which who whom how why this that these those it its i we you they he she
my our your their there here about into than then so if as any all per much many long time students student""".split())

_index_cache = {}  # (embedding model, chunk count, last chunk id) -> (faiss index, chunk ids)


def extract_pages(file_obj):
    """Return the text of every page (index 0 = page 1)."""
    reader = PdfReader(file_obj)
    return [(page.extract_text() or "") for page in reader.pages]


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks, cutting at sentence ends when possible."""
    text = re.sub(r"\s+", " ", text).strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind(". ", start + size // 2, end)  # prefer to end at a full stop
            end = cut + 1 if cut != -1 else end
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def ingest(document):
    """(Re)build the chunks of one document. Returns the number of chunks."""
    document.file.open("rb")
    try:
        pages = extract_pages(document.file)
    finally:
        document.file.close()

    embedder = embeddings.get_embedder()
    rows = []
    for page_number, page_text in enumerate(pages, start=1):
        for piece in chunk_text(page_text):
            rows.append((page_number, piece))

    vectors = embedder.embed([text for _, text in rows]) if rows else []
    DocumentChunk.objects.filter(document=document).delete()
    DocumentChunk.objects.bulk_create([
        DocumentChunk(document=document, page=page, chunk_index=i, text=text,
                      embedding=embeddings.to_bytes(vectors[i]), embedding_model=embedder.name)
        for i, (page, text) in enumerate(rows)
    ])
    document.pages = len(pages)
    document.save(update_fields=["pages"])
    return len(rows)


def _index():
    """FAISS index over all chunks, rebuilt only when chunks change."""
    model = embeddings.get_embedder().name
    chunks = DocumentChunk.objects.filter(embedding_model=model)
    key = (model, chunks.count(), chunks.order_by("-id").values_list("id", flat=True).first())
    if key not in _index_cache:
        _index_cache.clear()
        rows = list(chunks.values_list("id", "embedding"))
        if not rows:
            return None, []
        _index_cache[key] = (embeddings.build_index([embeddings.from_bytes(e) for _, e in rows]), [i for i, _ in rows])
    return _index_cache[key]


def keywords(text):
    """Content words of a text (lowercase, no stopwords, simple plural removal)."""
    words = re.findall(r"[a-z0-9]+|[\u0B80-\u0BFF\u0D00-\u0D7F]+", text.lower())
    return {w.rstrip("s") if len(w) > 3 else w for w in words if w not in STOPWORDS}


def keyword_score(query_words, text):
    """Fraction of the question's keywords that appear in the chunk (0..1)."""
    if not query_words:
        return 0.0
    return len(query_words & keywords(text)) / len(query_words)


def search(query, k=4, min_score=MIN_SCORE):
    """The k most relevant chunks: [{"file", "title", "page", "text", "score"}]."""
    index, ids = _index()
    if index is None:
        return []
    # 1. Embedding search for candidates (more than we need).
    vector = np.asarray([embeddings.embed_text(query)], dtype="float32")
    scores, positions = index.search(vector, min(k * 5, len(ids)))
    candidates = {ids[p]: float(s) for p, s in zip(positions[0], scores[0]) if p != -1}
    chunks = DocumentChunk.objects.select_related("document").in_bulk(list(candidates))

    # 2. Re-rank: mix embedding similarity with keyword overlap.
    query_words = keywords(query)
    ranked = []
    for chunk_id, similarity in candidates.items():
        chunk = chunks[chunk_id]
        score = (1 - KEYWORD_WEIGHT) * similarity + KEYWORD_WEIGHT * keyword_score(query_words, chunk.text)
        if score >= min_score:
            ranked.append((score, chunk))
    ranked.sort(key=lambda pair: -pair[0])
    return [
        {"file": c.document.file_name, "title": c.document.title, "page": c.page, "text": c.text, "score": round(s, 3)}
        for s, c in ranked[:k]
    ]
