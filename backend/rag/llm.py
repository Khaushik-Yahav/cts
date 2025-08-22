from __future__ import annotations
import os
import time
from typing import Literal, Optional

Provider = Literal["groq", "gemini", "openai", "auto"]

SYSTEM_BASE = (
    "You are a careful medical assistant. "
    "Answer ONLY from the provided context. "
    "If unsure, say you do not know. "
    "Be precise and concise in your responses."
)

def generate_answer(
    prompt: str,
    provider: Provider = "auto",
    model_override: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> str:
    """
    Generate answer with automatic fallback between providers.
    Priority: Groq -> Gemini -> OpenAI
    """

    # Try Groq first
    if os.getenv("GROQ_API_KEY"):
        try:
            from groq import Groq
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            model = model_override or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

            messages = [
                {"role": "system", "content": SYSTEM_BASE},
                {"role": "user", "content": prompt},
            ]

            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1,
                stream=False,
            )
            return (completion.choices[0].message.content or "").strip()

        except Exception as e:
            print(f"Groq failed: {e}")

    # Try Gemini as fallback
    if os.getenv("GEMINI_API_KEY"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = model_override or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            model_instance = genai.GenerativeModel(model)

            # Convert prompt for Gemini
            full_prompt = f"System: {SYSTEM_BASE}\n\nUser: {prompt}"

            response = model_instance.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
            return response.text.strip()

        except Exception as e:
            print(f"Gemini failed: {e}")

    # Try OpenAI as final fallback
    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            model = model_override or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

            messages = [
                {"role": "system", "content": SYSTEM_BASE},
                {"role": "user", "content": prompt},
            ]

            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1,
                stream=False,
            )
            return (completion.choices[0].message.content or "").strip()

        except Exception as e:
            print(f"OpenAI failed: {e}")

    return "[No LLM providers available or all failed]"

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

    if summary.startswith("[No LLM providers"):
        return text[:1000]  # Fallback to truncated text

    return summary.strip()
