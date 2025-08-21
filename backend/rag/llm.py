'''
from __future__ import annotations
import os
from groq import Groq

def _use_groq() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))

def generate_answer(prompt: str) -> str:
    if _use_groq():
        try:
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            completion = client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                messages=[
                    {"role": "system", "content": "You are a careful medical assistant. Answer ONLY from the provided context. If unsure, say you do not know."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_completion_tokens=1024,
                top_p=1,
                stream=False
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return f"[Groq LLM error: {e}]"

    return "[No LLM configured. Set GROQ_API_KEY in .env]"
'''
"""
from __future__ import annotations
import os
from groq import Groq
from openai import OpenAI

def _use_groq() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))

def _use_openai() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))

def generate_answer(prompt: str) -> str:
    if _use_groq():
        try:
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            completion = client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                messages=[
                    {"role": "system", "content": "You are a careful medical assistant. Answer ONLY from the provided context. If unsure, say you do not know."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_completion_tokens=1024
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return f"[Groq LLM error: {e}]"

    elif _use_openai():
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            completion = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a careful medical assistant. Answer ONLY from the provided context. If unsure, say you do not know."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=800
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return f"[OpenAI LLM error: {e}]"

    return "[No LLM configured. Set GROQ_API_KEY or OPENAI_API_KEY in .env]"
"""
"""
from __future__ import annotations
import os
from typing import Literal, Optional
from groq import Groq
from openai import OpenAI

Provider = Literal["groq", "openai", "auto"]

SYSTEM_BASE = "You are a careful medical assistant. Answer ONLY from the provided context. If unsure, say you do not know."

def _has_groq() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))

def _has_openai() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))

def _pick_provider(preferred: Provider) -> Provider:
    if preferred == "groq" and _has_groq():
        return "groq"
    if preferred == "openai" and _has_openai():
        return "openai"
    # auto fallback
    if _has_groq():
        return "groq"
    if _has_openai():
        return "openai"
    return "auto"  # means: nothing available

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
                max_completion_tokens=max_tokens,
                top_p=1,
                stream=False,
            )
            return completion.choices[0].message.content.strip()
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
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return f"[OpenAI LLM error: {e}]"

    return "[No LLM configured. Set GROQ_API_KEY or OPENAI_API_KEY in .env]"

def summarize_history(
    text: str,
    provider: Provider = "auto",
    model_override: Optional[str] = None,
    max_tokens: int = 600,
) -> str:
    """
    Summarize older turns into a concise rolling summary included in prompts.
    """
    sys = "You are a concise summarizer for a medical Q&A assistant. Produce a short, factual summary of the dialogue so far that preserves important clinical context and decisions. Avoid speculation."
    chosen = _pick_provider(provider)
    if chosen == "groq":
        try:
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            model = model_override or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_completion_tokens=max_tokens,
                stream=False,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return f"[Summary error (Groq): {e}]"

    if chosen == "openai":
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            model = model_override or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=max_tokens,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return f"[Summary error (OpenAI): {e}]"

    return ""
"""
from __future__ import annotations
import os
from typing import Literal, Optional
from groq import Groq
from openai import OpenAI


Provider = Literal["groq", "openai", "auto"]


SYSTEM_BASE = "You are a careful medical assistant. Answer ONLY from the provided context. If unsure, say you do not know."


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
max_completion_tokens=max_tokens,
top_p=1,
stream=False,
)
return completion.choices[0].message.content.strip()
except Exception as e:
return f"[Groq LLM error: {e}]"


if chosen == "openai":
try:
model=m