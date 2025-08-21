from __future__ import annotations
import os, shutil
from typing import Optional, Literal
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from sqlalchemy import select
from backend.rag.qa import answer_question
from backend.rag.ingest import ingest_pdfs
from backend.db import db_session, engine
from backend.models import Base, ChatSession, Message, User
from backend.auth import get_current_user, AuthUser, hash_password, verify_password, create_access_token

load_dotenv()

disable_swagger = bool(os.getenv("DISABLE_SWAGGER_UI"))
app = FastAPI(
    title="Drug Info RAG API",
    docs_url=None if disable_swagger else "/docs",
    redoc_url=None if disable_swagger else "/redoc",
)

# CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB bootstrap ---
def init_db():
    Base.metadata.create_all(bind=engine)
init_db()

# --- Schemas ---
Provider = Literal["groq", "openai", "auto"]

class AskBody(BaseModel):
    question: str
    session_id: Optional[str] = None
    top_k: int = 4
    provider: Provider = "auto"       # "groq" | "openai" | "auto"
    model: Optional[str] = None       # override model per request

class NewSessionBody(BaseModel):
    title: Optional[str] = None

class RenameSessionBody(BaseModel):
    title: str

class RegisterBody(BaseModel):
    email: EmailStr
    password: str

class LoginBody(BaseModel):
    email: EmailStr
    password: str

@app.get("/health")
def health():
    return {"ok": True}

# ---------- Auth ----------
@app.post("/auth/register")
def register(body: RegisterBody):
    with db_session() as db:
        exists = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=400, detail="Email already registered")
        u = User(email=body.email, password_hash=hash_password(body.password))
        db.add(u)
        db.flush()
        token = create_access_token(u.id, u.email)
        return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/login")
def login(body: LoginBody):
    with db_session() as db:
        u = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
        if not u or not verify_password(body.password, u.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token(u.id, u.email)
        return {"access_token": token, "token_type": "bearer"}

# ---------- RAG ingestion / upload ----------
@app.post("/ingest")
async def ingest_endpoint(
    pdf_dir: str = "data/pdfs",
    index_dir: str = "data/index",
    user: AuthUser = Depends(get_current_user),
):
    try:
        stats = ingest_pdfs(pdf_dir=pdf_dir, index_dir=index_dir)
        return {"status": "ok", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
):
    try:
        os.makedirs("data/pdfs", exist_ok=True)
        dest = os.path.join("data/pdfs", file.filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        stats = ingest_pdfs(pdf_dir="data/pdfs", index_dir="data/index")
        return {"status": "uploaded", "file": file.filename, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF upload failed: {e}")

# ---------- Chat/Q&A ----------
@app.post("/ask")
async def ask(body: AskBody, user: AuthUser = Depends(get_current_user)):
    """
    Choose provider/model per request. Creates a session if none provided.
    """
    # Ensure index exists early
    if not (os.path.exists("data/index/index.faiss") and os.path.exists("data/index/meta.json")):
        raise HTTPException(status_code=400, detail="No index found. Upload/ingest PDFs first.")

    try:
        effective_session_id = body.session_id
        if effective_session_id is None:
            with db_session() as db:
                s = ChatSession(user_id=user.id, title="New chat")
                db.add(s)
                db.flush()
                effective_session_id = s.id
        else:
            with db_session() as db:
                s = db.get(ChatSession, effective_session_id)
                if not s or s.user_id != user.id:
                    raise HTTPException(status_code=404, detail="Session not found")

        text, citations, _ = answer_question(
            question=body.question,
            session_id=effective_session_id,
            top_k=body.top_k,
            index_dir="data/index",
            provider=body.provider,
            model_override=body.model,
        )
        return {"answer": text, "citations": citations, "session_id": effective_session_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Q&A failed: {e}")

# ---------- Sessions (left sidebar) ----------
@app.get("/sessions")
def list_sessions(user: AuthUser = Depends(get_current_user)):
    with db_session() as db:
        rows = db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user.id)
            .order_by(ChatSession.updated_at.desc())
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
def create_session(body: NewSessionBody, user: AuthUser = Depends(get_current_user)):
    with db_session() as db:
        s = ChatSession(user_id=user.id, title=body.title or "New chat")
        db.add(s)
        db.flush()
        return {"id": s.id, "title": s.title, "created_at": s.created_at, "updated_at": s.updated_at}

@app.get("/sessions/{session_id}")
def get_session(session_id: str, user: AuthUser = Depends(get_current_user)):
    with db_session() as db:
        s = db.get(ChatSession, session_id)
        if not s or s.user_id != user.id:
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
def rename_session(session_id: str, body: RenameSessionBody, user: AuthUser = Depends(get_current_user)):
    with db_session() as db:
        s = db.get(ChatSession, session_id)
        if not s or s.user_id != user.id:
            raise HTTPException(status_code=404, detail="Session not found")
        s.title = body.title
        return {"id": s.id, "title": s.title}

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, user: AuthUser = Depends(get_current_user)):
    with db_session() as db:
        s = db.get(ChatSession, session_id)
        if not s or s.user_id != user.id:
            raise HTTPException(status_code=404, detail="Session not found")
        db.delete(s)
        return {"deleted": True}
