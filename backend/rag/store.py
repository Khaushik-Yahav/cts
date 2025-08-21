from __future__ import annotations
import os, json, faiss, numpy as np
from typing import Any

def save_index(index_dir: str, index: faiss.IndexFlatIP, embeddings: np.ndarray, metadatas: list[dict[str, Any]]):
    os.makedirs(index_dir, exist_ok=True)
    faiss.write_index(index, os.path.join(index_dir, "index.faiss"))
    np.save(os.path.join(index_dir, "embeddings.npy"), embeddings)
    with open(os.path.join(index_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(metadatas, f, ensure_ascii=False, indent=2)

def load_index(index_dir: str):
    index_path = os.path.join(index_dir, "index.faiss")
    embs_path = os.path.join(index_dir, "embeddings.npy")
    meta_path = os.path.join(index_dir, "meta.json")
    if not (os.path.exists(index_path) and os.path.exists(embs_path) and os.path.exists(meta_path)):
        raise FileNotFoundError("Index not found. Run ingestion first.")
    index = faiss.read_index(index_path)
    embeddings = np.load(embs_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        metadatas = json.load(f)
    return index, embeddings, metadatas
