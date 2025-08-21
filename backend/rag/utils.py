from __future__ import annotations
import re

def clean_text(t: str) -> str:
    # Basic cleanup: collapse spaces, normalize bullets
    t = t.replace('\u2022', '-').replace('\u00b7', '-')
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n{2,}', '\n\n', t)
    return t.strip()

def chunk_text(text: str, max_tokens: int = 800, overlap: int = 120) -> list[str]:
    # Approximate tokenization by words; good enough to start
    words = text.split()
    chunks = []
    i = 0
    step = max_tokens - overlap
    while i < len(words):
        chunk_words = words[i:i+max_tokens]
        chunks.append(' '.join(chunk_words))
        i += step
    return chunks
