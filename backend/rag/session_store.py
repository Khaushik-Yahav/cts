from __future__ import annotations
from typing import Dict, List

# session_logs: {session_id: [{"question": str, "answer": str, "citations": list}]}
session_logs: Dict[str, List[Dict]] = {}

def add_to_session(session_id: str, question: str, answer: str, citations: list):
    if session_id not in session_logs:
        session_logs[session_id] = []
    session_logs[session_id].append({
        "question": question,
        "answer": answer,
        "citations": citations
    })

def get_session_context(session_id: str) -> str:
    if session_id not in session_logs:
        return ""
    history_text = []
    for qa in session_logs[session_id]:
        history_text.append(f"Q: {qa['question']}\nA: {qa['answer']}")
    return "\n\n".join(history_text)
