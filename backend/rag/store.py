from __future__ import annotations

import os
import json
import faiss
import numpy as np
from typing import Any

def save_index(index_dir: str, index: faiss.IndexFlatIP, embeddings: np.ndarray, metadatas: list[dict[str, Any]]):
    """Save FAISS index, embeddings, and metadata to disk"""
    os.makedirs(index_dir, exist_ok=True)

    # Save FAISS index
    faiss.write_index(index, os.path.join(index_dir, "index.faiss"))

    # Save embeddings
    np.save(os.path.join(index_dir, "embeddings.npy"), embeddings)

    # Save metadata
    with open(os.path.join(index_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(metadatas, f, ensure_ascii=False, indent=2)

def load_index(index_dir: str):
    """Load FAISS index, embeddings, and metadata from disk"""
    index_path = os.path.join(index_dir, "index.faiss")
    embs_path = os.path.join(index_dir, "embeddings.npy")
    meta_path = os.path.join(index_dir, "meta.json")

    # Check if all required files exist
    if not all(os.path.exists(path) for path in [index_path, embs_path, meta_path]):
        raise FileNotFoundError(
            f"Index files not found in {index_dir}. "
            "Please upload and ingest PDFs first."
        )

    # Load files
    index = faiss.read_index(index_path)
    embeddings = np.load(embs_path)

    with open(meta_path, "r", encoding="utf-8") as f:
        metadatas = json.load(f)

    return index, embeddings, metadatas

def index_exists(index_dir: str) -> bool:
    """Check if a valid index exists"""
    try:
        load_index(index_dir)
        return True
    except FileNotFoundError:
        return False
