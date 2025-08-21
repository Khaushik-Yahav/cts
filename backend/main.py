from __future__ import annotations
import os, shutil
from typing import Optional, Literal
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import select
from backend.rag.qa import answer_question
from backend.rag.ingest import ingest_pdfs
from backend.db import db_session, engine
from backend.models import Base, ChatSession, Message

load_dotenv()

disable_swagger = bool(os.getenv("DISABLE_SWAGGER_UI"))
app = FastAPI(
    title="Drug Info RAG API",
    docs_url=None if disable_swagger else "/docs",
    redoc_url=None if disable_swagger else "/redoc",
)

# --- DB bootstrap ---
def init_db():
    Base.metadata.create_all(bind=engine)

init_db()

# --- Schemas ---
Provider = Literal["groq", "openai", "auto"]

class AskBody(BaseModel):
    question: str
    session_id: Optional[str] = None    # pass null to create a new chat implicitly
    top_k: int = 4
    provider: Provider = "auto"         # NEW: "groq" | "openai" | "auto"
    model: Optional[str] = None         # NEW: override model per request

class NewSessionBody(BaseModel):
    title: Optional[str] = None

class RenameSessionBody(BaseModel):
    title: str

@app.get("/health")
def health():
    return {"ok": True}

# ---------- RAG ingestion / upload ----------
@app.post("/ingest")
async def ingest_endpoint(pdf_dir: str = "data/pdfs", index_dir: str = "data/index"):
    try:
        stats = ingest_pdfs(pdf_dir=pdf_dir, index_dir=index_dir)
        return {"status": "ok", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        os.makedirs("data/pdfs", exist_ok=True)
        dest = os.path.join("data/pdfs", file.filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        # Rebuild index after each upload
        stats = ingest_pdfs(pdf_dir="data/pdfs", index_dir="data/index")
        return {"status": "uploaded", "file": file.filename, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF upload failed: {e}")

# ---------- Chat/Q&A ----------
@app.post("/ask")
async def ask(body: AskBody):
    """
    Dynamically choose LLM provider/model per request.
    If body.session_id is None, a new session is created implicitly and returned.
    """
    try:
        text, citations, effective_session_id = answer_question(
            question=body.question,
            session_id=body.session_id,
            top_k=body.top_k,
            index_dir="data/index",
            provider=body.provider,
            model_override=body.model,
        )
        return {
            "answer": text,
            "citations": citations,
            "session_id": effective_session_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Q&A failed: {e}")

# ---------- Sessions (for left sidebar like ChatGPT) ----------
@app.get("/sessions")
def list_sessions():
    with db_session() as db:
        rows = db.execute(
            select(ChatSession).order_by(ChatSession.updated_at.desc())
        ).scalars()
        return [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in rows
        ]

@app.post("/sessions")
def create_session(body: NewSessionBody):
    with db_session() as db:
        s = ChatSession(title=body.title or "New chat")
        db.add(s)
        db.flush()
        return {"id": s.id, "title": s.title, "created_at": s.created_at, "updated_at": s.updated_at}

@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    with db_session() as db:
        s = db.get(ChatSession, session_id)
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "id": s.id,
            "title": s.title,
            "summary": s.summary,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role.value,
                    "content": m.content,
                    "citations": m.citations,
                    "created_at": m.created_at,
                }
                for m in s.messages
            ],
        }

@app.patch("/sessions/{session_id}")
def rename_session(session_id: str, body: RenameSessionBody):
    with db_session() as db:
        s = db.get(ChatSession, session_id)
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        s.title = body.title
        return {"id": s.id, "title": s.title}

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    with db_session() as db:
        s = db.get(ChatSession, session_id)
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        db.delete(s)
        return {"deleted": True}

"""
import os
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from dotenv import load_dotenv
from backend.rag.qa import answer_question
from backend.rag.ingest import ingest_pdfs

load_dotenv()

app = FastAPI(title="Drug Info RAG API")

class AskBody(BaseModel):
    question: str
    session_id: str | None = None
    top_k: int = 4

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ingest")
async def ingest_endpoint(pdf_dir: str = "data/pdfs", index_dir: str = "data/index"):
    stats = ingest_pdfs(pdf_dir=pdf_dir, index_dir=index_dir)
    return {"status":"ok", "stats": stats}

@app.post("/ask")
async def ask(body: AskBody):
    text, citations = answer_question(
        question=body.question,
        session_id=body.session_id or "default",
        top_k=body.top_k,
        index_dir="data/index"
    )
    return {"answer": text, "citations": citations}
"""
"""
import os, shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from backend.rag.qa import answer_question
from backend.rag.ingest import ingest_pdfs

load_dotenv()

app = FastAPI(title="Drug Info RAG API")

class AskBody(BaseModel):
    question: str
    session_id: str | None = None
    top_k: int = 4

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ingest")
async def ingest_endpoint(pdf_dir: str = "data/pdfs", index_dir: str = "data/index"):
    try:
        stats = ingest_pdfs(pdf_dir=pdf_dir, index_dir=index_dir)
        return {"status": "ok", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        os.makedirs("data/pdfs", exist_ok=True)
        dest = os.path.join("data/pdfs", file.filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        # Rebuild index after each upload
        stats = ingest_pdfs(pdf_dir="data/pdfs", index_dir="data/index")
        return {"status": "uploaded", "file": file.filename, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF upload failed: {e}")

@app.post("/ask")
async def ask(body: AskBody):
    try:
        text, citations = answer_question(
            question=body.question,
            session_id=body.session_id or "default",
            top_k=body.top_k,
            index_dir="data/index"
        )
        return {"answer": text, "citations": citations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Q&A failed: {e}")
"""