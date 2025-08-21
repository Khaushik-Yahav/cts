from __future__ import annotations
from typing import Tuple, List, Dict, Literal, Optional
from sqlalchemy import select
from backend.rag.retrieve import retrieve
from backend.rag.llm import generate_answer, summarize_history, Provider
from backend.db import db_session
from backend.models import ChatSession, Message, RoleEnum

# How much history to include verbatim in prompts
MAX_QA_PAIRS_IN_PROMPT = 20  # safe default; you asked me to choose

PROMPT_TEMPLATE = '''You are answering a user question strictly using the CONTEXT.
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
'''

def _format_context(chunks: List[Dict]) -> str:
    parts = []
    for c in chunks:
        header = f"[{c['source']} p.{c['page']}]"
        parts.append(header + "\n" + c["text"])
    return "\n\n".join(parts)

def _format_history(pairs: List[Dict]) -> str:
    # pairs: [{"q": "...", "a": "..."}]
    return "\n\n".join([f"Q: {p['q']}\nA: {p['a']}" for p in pairs])

def _load_or_create_session(session_id: Optional[str], title_fallback: str = "New chat") -> ChatSession:
    with db_session() as db:
        if session_id:
            obj = db.get(ChatSession, session_id)
            if obj:
                return obj
        # create new
        obj = ChatSession(title=title_fallback)
        db.add(obj)
        db.flush()  # populate obj.id
        return obj

def _get_last_n_qa_pairs(db, session_id: str, n_pairs: int) -> List[Dict]:
    # fetch last messages and build pairs
    stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
    messages = list(db.execute(stmt).scalars())
    pairs: List[Dict] = []
    cur_q = None
    for m in messages:
        if m.role == RoleEnum.user:
            cur_q = m.content
        elif m.role == RoleEnum.assistant and cur_q is not None:
            pairs.append({"q": cur_q, "a": m.content})
            cur_q = None
    return pairs[-n_pairs:]

def _maybe_update_summary(db, sess: ChatSession, provider: Provider):
    """
    If pairs exceed MAX_QA_PAIRS_IN_PROMPT, summarize older pairs into sess.summary.
    We keep *all* messages in DB, but only include last N pairs + summary in prompts.
    """
    pairs_all = _get_last_n_qa_pairs(db, sess.id, 10_000)  # effectively all
    if len(pairs_all) <= MAX_QA_PAIRS_IN_PROMPT:
        return

    older = pairs_all[:-MAX_QA_PAIRS_IN_PROMPT]
    if not older:
        return

    older_text = _format_history(older)
    rolled = summarize_history(older_text, provider=provider)
    # Append (or replace) rolling summary.
    if sess.summary:
        sess.summary = sess.summary + "\n\n" + rolled
    else:
        sess.summary = rolled

def answer_question(
    question: str,
    session_id: Optional[str],
    top_k: int,
    index_dir: str,
    provider: Provider = "auto",
    model_override: Optional[str] = None,
) -> Tuple[str, List[Dict], str]:
    """
    Returns: answer, citations, effective_session_id
    """
    # Ensure session exists
    sess = _load_or_create_session(session_id)
    effective_session_id = sess.id

    with db_session() as db:
        sess = db.get(ChatSession, effective_session_id)

        # 1) Store the user message
        user_msg = Message(session_id=sess.id, role=RoleEnum.user, content=question)
        db.add(user_msg)
        db.flush()

        # 2) Retrieve
        hits = retrieve(question, index_dir=index_dir, top_k=top_k)

        # 3) Build prompt using rolling summary + last N pairs
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

        # 4) LLM
        answer = generate_answer(
            prompt,
            provider=provider,
            model_override=model_override,
        )

        # 5) Citations for API response
        citations = [{"source": h["source"], "page": h["page"], "score": h["score"], "rank": h["rank"]} for h in hits]

        # 6) Store assistant message
        asst_msg = Message(session_id=sess.id, role=RoleEnum.assistant, content=answer, citations=citations)
        db.add(asst_msg)

        # 7) Maybe roll up older turns to summary
        _maybe_update_summary(db, sess, provider=provider)

        # 8) Touch updated_at
        from datetime import datetime
        sess.updated_at = datetime.utcnow()

        return answer, citations, effective_session_id



"""
from __future__ import annotations
from typing import Tuple, List, Dict
from backend.rag.retrieve import retrieve
from backend.rag.llm import generate_answer

PROMPT_TEMPLATE = '''You are answering a user question strictly using the CONTEXT.
If the answer is not in the context, say "I don't know based on the provided documents."

QUESTION:
{question}

CONTEXT (each item shows [source p.page] headers):
{context}

Return a concise answer suitable for clinicians and patients. End with citations like:
[CITATIONS: filename p.X, filename p.Y].
'''

def _format_context(chunks: List[Dict]) -> str:
    parts = []
    for c in chunks:
        header = f"[{c['source']} p.{c['page']}]"
        parts.append(header + "\n" + c["text"])
    return "\n\n".join(parts)

def answer_question(question: str, session_id: str, top_k: int, index_dir: str) -> Tuple[str, List[Dict]]:
    # 1) Retrieve
    hits = retrieve(question, index_dir=index_dir, top_k=top_k)

    # 2) Build prompt
    context = _format_context(hits)
    prompt = PROMPT_TEMPLATE.format(question=question, context=context)

    # 3) LLM
    answer = generate_answer(prompt)

    # 4) Citations for API response
    citations = [{"source": h["source"], "page": h["page"], "score": h["score"], "rank": h["rank"]} for h in hits]
    return answer, citations

"""

"""
from __future__ import annotations
from typing import Tuple, List, Dict
from backend.rag.retrieve import retrieve
from backend.rag.llm import generate_answer
from backend.rag.session_store import add_to_session, get_session_context

PROMPT_TEMPLATE = '''You are answering a user question strictly using the CONTEXT.
If the answer is not in the context, say "I don't know based on the provided documents."

SESSION CONTEXT (earlier Q&A for reference):
{session_context}

QUESTION:
{question}

DOCUMENT CONTEXT (retrieved passages with [source p.page] headers):
{context}

Return a concise answer suitable for clinicians and patients. 
End with citations like: [CITATIONS: filename p.X, filename p.Y].
'''

def _format_context(chunks: List[Dict]) -> str:
    parts = []
    for c in chunks:
        header = f"[{c['source']} p.{c['page']}]"
        parts.append(header + "\n" + c["text"])
    return "\n\n".join(parts)

def answer_question(question: str, session_id: str, top_k: int, index_dir: str) -> Tuple[str, List[Dict]]:
    try:
        # 1) Retrieve
        hits = retrieve(question, index_dir=index_dir, top_k=top_k)

        # 2) Build prompt with history
        session_context = get_session_context(session_id)
        context = _format_context(hits)
        prompt = PROMPT_TEMPLATE.format(session_context=session_context, question=question, context=context)

        # 3) LLM
        answer = generate_answer(prompt)

        # 4) Citations for API response
        citations = [{"source": h["source"], "page": h["page"], "score": h["score"], "rank": h["rank"]} for h in hits]

        # 5) Save to session log
        add_to_session(session_id, question, answer, citations)

        return answer, citations

    except FileNotFoundError:
        return "[Error: No index found. Please ingest PDFs first.]", []
    except Exception as e:
        return f"[Unexpected error: {e}]", []
"""