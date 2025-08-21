from __future__ import annotations
import os, fitz, faiss, numpy as np
from typing import Dict, Any
from backend.rag.utils import clean_text, chunk_text
from backend.rag.embeddings import embed_texts
from backend.rag.store import save_index

def extract_pdf_pages(path: str) -> list[dict[str, Any]]:
    doc = fitz.open(path)
    out = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text")
        out.append({"page": i, "text": text})
    doc.close()
    return out

def ingest_pdfs(pdf_dir: str = "data/pdfs", index_dir: str = "data/index") -> Dict[str, Any]:
    # 1) Read and combine all PDFs
    entries = []
    for fn in os.listdir(pdf_dir):
        if not fn.lower().endswith(".pdf"):
            continue
        full = os.path.join(pdf_dir, fn)
        pages = extract_pdf_pages(full)
        for p in pages:
            cleaned = clean_text(p["text"] or "")
            if not cleaned:
                continue
            # Chunk per page so we retain page citations
            for chunk in chunk_text(cleaned, max_tokens=800, overlap=120):
                entries.append({
                    "text": chunk,
                    "page": p["page"],
                    "source": fn
                })
    if not entries:
        return {"chunks": 0, "message": "No PDFs or no text extracted."}

    # 2) Embed
    texts = [e["text"] for e in entries]
    embs = embed_texts(texts)  # (N, D)

    # 3) Build FAISS index (cosine sim via inner product b/c normalized)
    dim = embs.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embs)

    # 4) Persist
    save_index(index_dir=index_dir, index=index, embeddings=embs, metadatas=entries)

    return {"chunks": len(entries), "index_dir": index_dir, "pdf_count": len([f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')])}
