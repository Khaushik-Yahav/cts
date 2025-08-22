from __future__ import annotations
import faiss
from typing import List, Dict, Any
from backend.rag.embeddings import embed_texts
from backend.rag.store import load_index

def retrieve(query: str, index_dir: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """
    Retrieve relevant documents for a given query.
    Returns list of results with scores, text, and metadata.
    """
    try:
        index, _embeddings, metadatas = load_index(index_dir)
    except FileNotFoundError as e:
        raise ValueError(f"No search index found: {e}")

    # Embed the query
    qvec = embed_texts([query])  # Shape: (1, D)

    # Search for similar documents
    scores, indices = index.search(qvec, top_k)

    results: List[Dict[str, Any]] = []

    for rank, (idx, score) in enumerate(zip(indices[0], scores[0])):
        if idx == -1:  # No more results
            continue

        meta = metadatas[int(idx)]
        results.append({
            "rank": rank + 1,
            "score": float(score),
            "text": meta["text"],
            "page": meta["page"],
            "source": meta["source"],
        })

    return results
