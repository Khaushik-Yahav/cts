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
    if qvec is None or qvec.size == 0:
        raise ValueError("Query embedding returned empty vector.")

    # Search for more candidates to filter
    search_k = min(top_k * 3, len(metadatas))  # Get 3x candidates for filtering
    scores, indices = index.search(qvec, search_k)

    results: List[Dict[str, Any]] = []

    # Improved similarity threshold - more lenient
    SIMILARITY_THRESHOLD = 0.25  # Lower threshold for better recall

    for rank, (idx, score) in enumerate(zip(indices[0], scores[0])):
        if idx == -1:  # No more results
            continue

        # Filter by similarity threshold
        if score < SIMILARITY_THRESHOLD:
            print(f"Filtered out result with low score: {score:.3f}")
            continue

        meta = metadatas[int(idx)]
        
        # Skip very short chunks that likely won't be helpful
        if len(meta.get("text", "").strip()) < 50:
            continue

        results.append({
            "rank": rank + 1,
            "score": float(score),
            "text": meta["text"],
            "page": meta["page"],
            "source": meta["source"],
        })

    # Sort by score (descending) and return top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    
    print(f"Retrieved {len(results)} relevant documents for query: '{query[:50]}...'")
    for i, result in enumerate(results[:top_k]):
        print(f"  {i+1}. {result['source']} p.{result['page']} - Score: {result['score']:.3f}")

    return results[:top_k]
