# RX RAG Starter (FastAPI + FAISS)

### What you get
- Ingest PDFs → clean text → chunk → embed (Sentence-Transformers) → FAISS index
- `/ask` endpoint: retrieval-augmented answer with **PDF page citations**
- `/ingest` endpoint: ingest PDFs from `data/pdfs`
- Works with **OpenAI** (if `OPENAI_API_KEY` is set) or **Ollama** (if `OLLAMA_MODEL` is set)

### Quickstart
```bash
# 1) Create venv and install deps
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2) Put your PDFs in data/pdfs/
# e.g., Rinvoq label PDF

# 3) Ingest
python -m backend.rag.ingest --pdf_dir data/pdfs --index_dir data/index

# 4) Run API
uvicorn backend.main:app --reload

# 5) Ask a question
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json"   -d '{"question":"What is the recommended dosage for Crohn\'s disease?", "session_id":"demo"}'
```

### Notes
- No LLM training is required for RAG. You can add more PDFs anytime and re-run ingest.
- If you don’t set `OPENAI_API_KEY`, the server will try to use **Ollama** at `http://localhost:11434` with `OLLAMA_MODEL`.
