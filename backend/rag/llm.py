from __future__ import annotations
import os
from typing import Literal, Optional
from groq import Groq
from openai import OpenAI

Provider = Literal["groq", "openai", "auto"]

SYSTEM_BASE = (
    "You are a careful medical assistant. "
    "Answer ONLY from the provided context. "
    "If unsure, say you do not know."
)

def _has_groq() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))

def _has_openai() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))

def _pick_provider(preferred: Provider) -> Provider:
    if preferred == "groq" and _has_groq():
        return "groq"
    if preferred == "openai" and _has_openai():
        return "openai"
    if _has_groq():
        return "groq"
    if _has_openai():
        return "openai"
    return "auto"

def generate_answer(
    prompt: str,
    provider: Provider = "auto",
    model_override: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> str:
    chosen = _pick_provider(provider)

    if chosen == "groq":
        try:
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            model = model_override or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_BASE},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,   # <-- correct param name
                top_p=1,
                stream=False,
            )
            return (completion.choices[0].message.content or "").strip()
        except Exception as e:
            return f"[Groq LLM error: {e}]"

    if chosen == "openai":
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            model = model_override or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_BASE},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1,
                stream=False,
            )
            return (completion.choices[0].message.content or "").strip()
        except Exception as e:
            return f"[OpenAI LLM error: {e}]"

    return "[No valid LLM provider available]"

def summarize_history(text: str, provider: Provider = "auto", max_tokens: int = 200) -> str:
    """
    Condense older turns into a brief rolling summary.
    Uses the selected LLM if available; otherwise returns a trimmed fallback.
    """
    text = (text or "").strip()
    if not text:
        return ""

    prompt = (
        "Condense the following chat snippets into a short summary capturing key facts, "
        "decisions, and user preferences. Be concise:\n\n"
        f"{text}\n\nSummary:"
    )
    summary = generate_answer(prompt, provider=provider, max_tokens=max_tokens)
    if summary.startswith("[No valid LLM provider"):
        return text[:1000]
    return summary.strip()
