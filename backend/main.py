from __future__ import annotations
import os
import shutil
from typing import Optional, Literal, List
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from sqlalchemy import select, func

from backend.rag.qa import answer_question
from backend.rag.ingest import ingest_pdfs
from backend.rag.store import index_exists
from backend.db import db_session, init_database
from backend.models import ChatSession, Message, User
from backend.auth import (
    get_current_user, 
    AuthUser, 
    hash_password, 
    verify_password, 
    create_access_token
)

# Load environment variables
load_dotenv()

# Create FastAPI app
disable_swagger = os.getenv("DISABLE_SWAGGER_UI", "false").lower() == "true"
app = FastAPI(
    title="Medical RAG Chatbot API",
    description="RAG-powered medical chatbot with user authentication",
    version="1.0.0",
    docs_url=None if disable_swagger else "/docs",
    redoc_url=None if disable_swagger else "/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates for frontend
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
    print("✅ Frontend files mounted successfully")
except Exception as e:
    print(f"⚠️ Could not mount frontend files: {e}")
    templates = None

# Initialize database
init_database()

# Ensure data directories exist
os.makedirs("data/pdfs", exist_ok=True)
os.makedirs("data/index", exist_ok=True)

# Type definitions
Provider = Literal["groq", "gemini", "openai", "auto"]

# --- Request/Response Models ---
class AskBody(BaseModel):
    question: str
    session_id: Optional[int] = None
    top_k: int = 4
    provider: Provider = "auto"
    model: Optional[str] = None

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

class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    citations: Optional[List[dict]]
    created_at: datetime

# --- Frontend Routes ---
@app.get("/", response_class=HTMLResponse)
async def frontend(request: Request):
    """Serve the main frontend page"""
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return HTMLResponse("""
        <h1>🏥 Medical RAG Chatbot API</h1>
        <p><strong>Frontend templates not available.</strong></p>
        <p>📚 API Documentation: <a href="/docs">/docs</a></p>
        <p>🔍 Health Check: <a href="/health">/health</a></p>
        """)

# --- Health Check ---
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "index_exists": index_exists("data/index"),
        "timestamp": datetime.utcnow().isoformat()
    }

# --- Authentication Routes ---
@app.post("/auth/register")
def register(body: RegisterBody):
    """Register a new user"""
    with db_session() as db:
        # Check if user already exists
        existing = db.execute(
            select(User).where(User.email == body.email)
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=400, 
                detail="Email already registered"
            )

        # Create new user
        user = User(
            email=body.email,
            password_hash=hash_password(body.password)
        )
        db.add(user)
        db.flush()

        # Generate access token
        token = create_access_token(user.id, user.email)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {"id": user.id, "email": user.email}
        }

@app.post("/auth/login")
def login(body: LoginBody):
    """Login user"""
    with db_session() as db:
        user = db.execute(
            select(User).where(User.email == body.email)
        ).scalar_one_or_none()

        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(
                status_code=401, 
                detail="Invalid credentials"
            )

        token = create_access_token(user.id, user.email)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {"id": user.id, "email": user.email}
        }

@app.get("/auth/me")
def get_current_user_info(user: AuthUser = Depends(get_current_user)):
    """Get current user information"""
    return {"id": user.id, "email": user.email}

# --- File Upload & Ingestion Routes ---
@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
):
    """Upload a PDF file and add it to the knowledge base"""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF files are allowed"
        )

    try:
        # Save uploaded file
        os.makedirs("data/pdfs", exist_ok=True)
        file_path = os.path.join("data/pdfs", file.filename)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Re-index all PDFs
        stats = ingest_pdfs(pdf_dir="data/pdfs", index_dir="data/index")

        return {
            "status": "uploaded",
            "filename": file.filename,
            "stats": stats
        }

    except Exception as e:
        # Clean up file if ingestion failed
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=500, 
            detail=f"Upload failed: {str(e)}"
        )

@app.post("/ingest")
async def manual_ingest(
    pdf_dir: str = "data/pdfs",
    index_dir: str = "data/index",
    user: AuthUser = Depends(get_current_user),
):
    """Manually trigger PDF ingestion"""
    try:
        stats = ingest_pdfs(pdf_dir=pdf_dir, index_dir=index_dir)
        return {"status": "completed", "stats": stats}
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Ingestion failed: {str(e)}"
        )

# --- Chat/QA Routes ---
@app.post("/ask")
async def ask_question(body: AskBody, user: AuthUser = Depends(get_current_user)):
    """Ask a question to the RAG system"""

    # Check if index exists
    if not index_exists("data/index"):
        raise HTTPException(
            status_code=400, 
            detail="No knowledge base found. Please upload PDF files first."
        )

    try:
        # Create session if none provided
        effective_session_id = body.session_id
        if effective_session_id is None:
            with db_session() as db:
                session = ChatSession(user_id=user.id, title="New chat")
                db.add(session)
                db.flush()
                effective_session_id = session.id
        else:
            # Verify session ownership
            with db_session() as db:
                session = db.get(ChatSession, effective_session_id)
                if not session or session.user_id != user.id:
                    raise HTTPException(
                        status_code=404, 
                        detail="Session not found"
                    )

        # Get answer
        answer, citations, session_id, limit_reached = answer_question(
            question=body.question,
            session_id=effective_session_id,
            top_k=body.top_k,
            index_dir="data/index",
            provider=body.provider,
            model_override=body.model,
        )

        return {
            "answer": answer,
            "citations": citations,
            "session_id": session_id,
            "limit_reached": limit_reached
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Question processing failed: {str(e)}"
        )

# --- Session Management Routes ---
@app.get("/sessions", response_model=List[SessionResponse])
def list_sessions(user: AuthUser = Depends(get_current_user)):
    """Get all sessions for the current user"""
    with db_session() as db:
        sessions = db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user.id)
            .order_by(ChatSession.updated_at.desc())
        ).scalars().all()

        return [
            SessionResponse(
                id=s.id,
                title=s.title or "New chat",
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sessions
        ]

@app.post("/sessions", response_model=SessionResponse)
def create_session(
    body: NewSessionBody, 
    user: AuthUser = Depends(get_current_user)
):
    """Create a new chat session"""
    with db_session() as db:
        session = ChatSession(
            user_id=user.id,
            title=body.title or "New chat"
        )
        db.add(session)
        db.flush()

        return SessionResponse(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

@app.get("/sessions/{session_id}")
def get_session(
    session_id: int, 
    user: AuthUser = Depends(get_current_user)
):
    """Get a specific session with its messages"""
    with db_session() as db:
        session = db.get(ChatSession, session_id)
        if not session or session.user_id != user.id:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "id": session.id,
            "title": session.title,
            "summary": session.summary,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "messages": [
                MessageResponse(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    citations=m.citations,
                    created_at=m.created_at,
                )
                for m in session.messages
            ],
        }

@app.patch("/sessions/{session_id}", response_model=SessionResponse)
def rename_session(
    session_id: int,
    body: RenameSessionBody,
    user: AuthUser = Depends(get_current_user)
):
    """Rename a session"""
    with db_session() as db:
        session = db.get(ChatSession, session_id)
        if not session or session.user_id != user.id:
            raise HTTPException(status_code=404, detail="Session not found")

        session.title = body.title
        session.updated_at = datetime.utcnow()

        return SessionResponse(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

@app.delete("/sessions/{session_id}")
def delete_session(
    session_id: int, 
    user: AuthUser = Depends(get_current_user)
):
    """Delete a session"""
    with db_session() as db:
        session = db.get(ChatSession, session_id)
        if not session or session.user_id != user.id:
            raise HTTPException(status_code=404, detail="Session not found")

        db.delete(session)
        return {"deleted": True}

# --- Statistics Routes ---
@app.get("/stats")
def get_stats(user: AuthUser = Depends(get_current_user)):
    """Get user statistics"""
    with db_session() as db:
        session_count = db.execute(
            select(func.count(ChatSession.id))
            .where(ChatSession.user_id == user.id)
        ).scalar()

        message_count = db.execute(
            select(func.count(Message.id))
            .join(ChatSession)
            .where(ChatSession.user_id == user.id)
        ).scalar()

        return {
            "sessions": session_count or 0,
            "messages": message_count or 0,
            "index_exists": index_exists("data/index"),
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
