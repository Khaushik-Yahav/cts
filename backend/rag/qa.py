from __future__ import annotations
import os
from typing import Tuple, List, Dict, Optional
from sqlalchemy import select
from backend.rag.retrieve import retrieve
from backend.rag.llm import generate_answer, summarize_history, Provider
from backend.db import db_session
from backend.models import ChatSession, Message

# Configuration
MAX_MESSAGES_PER_SESSION = int(os.getenv("MAX_MESSAGES_PER_SESSION", "12"))
MAX_QA_PAIRS_IN_PROMPT = 6  # How many recent Q&A pairs to include in prompt

PROMPT_TEMPLATE = """You are answering a user question strictly using the CONTEXT.
If the answer is not in the context, say "I don't know based on the provided documents."

ROLLING SUMMARY (earlier dialogue condensed):
{rolling_summary}

RECENT CHAT (last {recent_n} QA pairs):
{recent_history}

QUESTION:
{question}

DOCUMENT CONTEXT (retrieved passages with [source p.page] headers):
{context}

Return a concise answer suitable for clinicians and patients.
End with citations like: [CITATIONS: filename p.X, filename p.Y].
"""

def _format_context(chunks: List[Dict]) -> str:
    """Format retrieved chunks for the prompt"""
    parts = []
    for c in chunks:
        header = f"[{c['source']} p.{c['page']}]"
        parts.append(header + "\n" + c["text"])
    return "\n\n".join(parts)

def _format_history(pairs: List[Dict]) -> str:
    """Format Q&A pairs for the prompt"""
    return "\n\n".join([f"Q: {p['q']}\nA: {p['a']}" for p in pairs])

def _get_last_n_qa_pairs(db, session_id: int, n_pairs: int) -> List[Dict]:
    """Get the last N Q&A pairs from a session"""
    stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
    messages = list(db.execute(stmt).scalars())

    pairs: List[Dict] = []
    cur_q = None

    for m in messages:
        if m.role == "user":
            cur_q = m.content
        elif m.role == "assistant" and cur_q is not None:
            pairs.append({"q": cur_q, "a": m.content})
            cur_q = None

    return pairs[-n_pairs:]

def _count_messages_in_session(db, session_id: int) -> int:
    """Count total messages in a session"""
    stmt = select(Message).where(Message.session_id == session_id)
    return len(list(db.execute(stmt).scalars()))

def _maybe_update_summary(db, sess: ChatSession, provider: Provider):
    """Update session summary if we have too many messages"""
    pairs_all = _get_last_n_qa_pairs(db, sess.id, 10_000)  # Get all pairs

    if len(pairs_all) <= MAX_QA_PAIRS_IN_PROMPT:
        return

    # Take older pairs for summarization
    older = pairs_all[:-MAX_QA_PAIRS_IN_PROMPT]
    if not older:
        return

    older_text = _format_history(older)
    rolled = summarize_history(older_text, provider=provider)

    if sess.summary:
        sess.summary = (sess.summary + "\n\n" + rolled).strip()
    else:
        sess.summary = rolled

def answer_question(
    question: str,
    session_id: int,
    top_k: int,
    index_dir: str,
    provider: Provider = "auto",
    model_override: Optional[str] = None,
) -> Tuple[str, List[Dict], int, bool]:
    """
    Answer a question using RAG.
    Returns: (answer, citations, session_id, session_limit_reached)
    """
    with db_session() as db:
        sess = db.get(ChatSession, session_id)
        if not sess:
            raise ValueError("Session not found")

        # Check if session limit is reached BEFORE adding new message
        message_count = _count_messages_in_session(db, sess.id)
        session_limit_reached = message_count >= MAX_MESSAGES_PER_SESSION

        if session_limit_reached:
            # Don't process the question, return limit message
            limit_message = (
                f"This session has reached the maximum limit of {MAX_MESSAGES_PER_SESSION} messages. "
                "Please start a new session to continue."
            )
            return limit_message, [], sess.id, True

        # Store the user message
        user_msg = Message(session_id=sess.id, role="user", content=question)
        db.add(user_msg)
        db.flush()

        try:
            # Retrieve relevant documents
            hits = retrieve(question, index_dir=index_dir, top_k=top_k)

            # Build prompt with context
            pairs_recent = _get_last_n_qa_pairs(db, sess.id, MAX_QA_PAIRS_IN_PROMPT)
            recent_history = _format_history(pairs_recent)
            context = _format_context(hits)

            prompt = PROMPT_TEMPLATE.format(
                rolling_summary=sess.summary or "",
                recent_n=len(pairs_recent),
                recent_history=recent_history,
                question=question,
                context=context,
            )

            # Generate answer
            answer = generate_answer(
                prompt,
                provider=provider,
                model_override=model_override,
            )

            # Format citations for API response
            citations = [
                {
                    "source": h["source"], 
                    "page": h["page"], 
                    "score": h["score"], 
                    "rank": h["rank"]
                } 
                for h in hits
            ]

        except Exception as e:
            answer = f"I apologize, but I encountered an error while processing your question: {str(e)}"
            citations = []

        # Store assistant message
        asst_msg = Message(
            session_id=sess.id, 
            role="assistant", 
            content=answer,
            citations=citations if citations else None
        )
        db.add(asst_msg)

        # Update summary if needed
        _maybe_update_summary(db, sess, provider=provider)

        # Update session timestamp
        from datetime import datetime
        sess.updated_at = datetime.utcnow()

        # Check if we're approaching the limit after adding these messages
        new_message_count = _count_messages_in_session(db, sess.id)
        approaching_limit = new_message_count >= MAX_MESSAGES_PER_SESSION

        return answer, citations, sess.id, approaching_limit
