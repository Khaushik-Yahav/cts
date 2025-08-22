from __future__ import annotations
import os
import fitz  # PyMuPDF
import faiss
import numpy as np
from typing import Dict, Any, List
from backend.rag.utils import clean_text, chunk_text
from backend.rag.embeddings import embed_texts
from backend.rag.store import save_index

def extract_pdf_pages(path: str) -> List[Dict[str, Any]]:
    """Extract text from PDF pages"""
    try:
        doc = fitz.open(path)
        pages = []

        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            pages.append({"page": i, "text": text})

        doc.close()
        return pages

    except Exception as e:
        print(f"Error extracting PDF {path}: {e}")
        return []

def ingest_pdfs(pdf_dir: str = "data/pdfs", index_dir: str = "data/index") -> Dict[str, Any]:
    """
    Process all PDFs in the directory and create/update the search index.
    Returns statistics about the ingestion process.
    """

    if not os.path.isdir(pdf_dir):
        return {
            "chunks": 0, 
            "message": f"PDF directory not found: {pdf_dir}",
            "pdf_count": 0,
            "success": False
        }

    entries = []
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]

    if not pdf_files:
        return {
            "chunks": 0,
            "message": "No PDF files found in directory",
            "pdf_count": 0,
            "success": False
        }

    print(f"Processing {len(pdf_files)} PDF files...")

    for filename in pdf_files:
        full_path = os.path.join(pdf_dir, filename)
        print(f"Processing: {filename}")

        pages = extract_pdf_pages(full_path)

        for page_info in pages:
            cleaned_text = clean_text(page_info["text"] or "")

            if not cleaned_text.strip():
                continue

            # Split into chunks
            chunks = chunk_text(cleaned_text, max_tokens=800, overlap=120)

            for chunk in chunks:
                if len(chunk.strip()) > 50:  # Only add substantial chunks
                    entries.append({
                        "text": chunk,
                        "page": page_info["page"],
                        "source": filename
                    })

    if not entries:
        return {
            "chunks": 0,
            "message": "No extractable text found in PDFs",
            "pdf_count": len(pdf_files),
            "success": False
        }

    print(f"Created {len(entries)} text chunks from {len(pdf_files)} PDFs")

    # Create embeddings
    print("Generating embeddings...")
    texts = [entry["text"] for entry in entries]
    embeddings = embed_texts(texts)  # Shape: (N, D)

    # Create FAISS index
    print("Building search index...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity with normalized vectors)
    index.add(embeddings)

    # Save everything
    print(f"Saving index to {index_dir}...")
    save_index(index_dir=index_dir, index=index, embeddings=embeddings, metadatas=entries)

    return {
        "chunks": len(entries),
        "index_dir": index_dir,
        "pdf_count": len(pdf_files),
        "success": True,
        "message": f"Successfully indexed {len(entries)} chunks from {len(pdf_files)} PDFs"
    }
