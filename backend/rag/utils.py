from __future__ import annotations
import re

def clean_text(t: str) -> str:
    """Clean and normalize text for better processing"""
    # Replace bullet points and special characters
    t = t.replace('\u2022', '-').replace('\u00b7', '-')
    # Normalize whitespace
    t = re.sub(r'[ \t]+', ' ', t)
    # Normalize line breaks
    t = re.sub(r'\n{2,}', '\n\n', t)
    return t.strip()

def chunk_text(text: str, max_tokens: int = 800, overlap: int = 120) -> list[str]:
    """
    Split text into overlapping chunks.
    Approximate tokens by words (rough estimation: 1 token ≈ 0.75 words)
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    i = 0
    step = max_tokens - overlap

    while i < len(words):
        chunk_words = words[i:i+max_tokens]
        chunk_text = ' '.join(chunk_words)
        if chunk_text.strip():  # Only add non-empty chunks
            chunks.append(chunk_text)
        i += step

    return chunks
