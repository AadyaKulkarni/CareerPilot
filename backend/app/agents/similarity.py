"""Text similarity ("embeddings") used for role/company/JD matching.

Default backend is TF-IDF (word 1-2 grams) which needs no API key and runs
offline. To use neural embeddings, replace `similarities()` with a function that
embeds the query and docs (e.g. OpenAI / sentence-transformers) and returns
cosine similarities in the same shape.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def similarities(query: str, docs: list[str]) -> list[float]:
    if not docs: return []
    if not (query or "").strip(): return [0.0] * len(docs)
    try:
        m = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)[A-Za-z0-9+#./]{2,}").fit_transform([query] + docs)
        return [float(x) for x in cosine_similarity(m[0:1], m[1:]).ravel()]
    except ValueError:  # empty vocabulary
        return [0.0] * len(docs)


def scaled(sim: float) -> float:
    """TF-IDF cosine between a CV and a short role description is rarely > 0.4; rescale to 0..1."""
    return max(0.0, min(1.0, sim * 2.5))
