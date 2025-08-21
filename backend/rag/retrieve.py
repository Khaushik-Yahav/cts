from __future__ import annotations
import numpy as np, faiss
from typing import List, Tuple, Dict, Any
from backend.rag.embeddings import embed_texts
from backend.rag.store import load_index

def retrieve(query: str, index_dir: str, top_k: int = 4) -> List[Dict[str, Any]]:
    index, embeddings, metadatas = load_index(index_dir)
    qvec = embed_texts([query])  # (1, D)
    D, I = index.search(qvec, top_k)  # distances, indices
    results = []
    for rank, idx in enumerate(I[0]):
        if idx == -1:
            continue
        meta = metadatas[int(idx)]
        results.append({
            "rank": rank + 1,
            "score": float(D[0][rank]),
            "text": meta["text"],
            "page": meta["page"],
            "source": meta["source"]
        })
    return results
