from __future__ import annotations

import re

def clean_text(t: str) -> str:
    """Clean and normalize text for better processing"""
    if not t:
        return ""
    
    # Replace bullet points and special characters
    t = t.replace('\u2022', '•').replace('\u00b7', '•')
    t = t.replace('\u2013', '-').replace('\u2014', '--')  # En/em dashes
    t = t.replace('\u201c', '"').replace('\u201d', '"')  # Smart quotes
    t = t.replace('\u2018', "'").replace('\u2019', "'")  # Smart apostrophes
    
    # Fix common PDF extraction issues
    t = re.sub(r'(\w)-\s+(\w)', r'\1\2', t)  # Fix hyphenated words split across lines
    t = re.sub(r'\s+', ' ', t)  # Normalize whitespace
    t = re.sub(r'\n{3,}', '\n\n', t)  # Reduce excessive line breaks
    
    # Clean up medical text formatting
    t = re.sub(r'(\d+)\s*\.\s*(\d+)', r'\1.\2', t)  # Fix decimal numbers
    t = re.sub(r'(\w)\s+%', r'\1%', t)  # Fix percentage spacing
    t = re.sub(r'(\d+)\s+(mg|mcg|g|ml|L)', r'\1 \2', t)  # Fix dosage units
    
    return t.strip()

def chunk_text(text: str, max_tokens: int = 800, overlap: int = 120) -> list[str]:
    """
    Split text into overlapping chunks with better sentence awareness.
    Approximate tokens by words (rough estimation: 1 token ≈ 0.75 words)
    """
    if not text or not text.strip():
        return []

    # First, try to split by sentences for more coherent chunks
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) <= 1:
        # Fallback to word-based chunking if no sentence boundaries
        words = text.split()
        if not words:
            return []
        return _chunk_by_words(words, max_tokens, overlap)

    chunks = []
    current_chunk = []
    current_length = 0
    
    i = 0
    while i < len(sentences):
        sentence = sentences[i].strip()
        sentence_length = len(sentence.split())
        
        # If adding this sentence would exceed max_tokens
        if current_length + sentence_length > max_tokens and current_chunk:
            # Create chunk from current sentences
            chunk_text = ' '.join(current_chunk).strip()
            if chunk_text and len(chunk_text) > 50:  # Only add substantial chunks
                chunks.append(chunk_text)
            
            # Start new chunk with overlap
            overlap_sentences = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
            current_chunk = overlap_sentences.copy()
            current_length = sum(len(s.split()) for s in current_chunk)
        
        # Add current sentence
        current_chunk.append(sentence)
        current_length += sentence_length
        i += 1
    
    # Add final chunk
    if current_chunk:
        chunk_text = ' '.join(current_chunk).strip()
        if chunk_text and len(chunk_text) > 50:
            chunks.append(chunk_text)
    
    print(f"Created {len(chunks)} chunks from text of length {len(text)}")
    return chunks

def _chunk_by_words(words: list[str], max_tokens: int = 800, overlap: int = 120) -> list[str]:
    """Fallback word-based chunking"""
    chunks = []
    i = 0
    step = max_tokens - overlap

    while i < len(words):
        chunk_words = words[i:i+max_tokens]
        chunk_text = ' '.join(chunk_words)
        if chunk_text.strip() and len(chunk_text) > 50:  # Only add substantial chunks
            chunks.append(chunk_text)
        i += step

    return chunks
