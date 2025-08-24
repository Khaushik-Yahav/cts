from __future__ import annotations

import os
import time
import re
from typing import Literal, Optional, List

Provider = Literal["groq", "gemini", "openai", "auto"]


SYSTEM_BASE = (
    "You are a helpful medical information assistant. "
    "Provide accurate, evidence-based responses using the context provided. "
    "For simple questions, give concise 1-2 sentence answers. "
    "For complex medical topics, provide detailed explanations in multiple bullet points. "
    "Always cite sources when using provided context. "
    "If information isn't in the context, acknowledge this and provide general medical guidance when appropriate."
)


QUERY_REWRITING_PROMPT = (
    "You are a medical query rewriting assistant. Given a medical question, generate 3-4 alternative "
    "ways to ask the same question that might retrieve different but relevant information. "
    "Focus on:\n"
    "- Using medical synonyms and terminology\n"
    "- Different phrasings (symptoms vs conditions vs treatments)\n"
    "- Varying specificity levels\n"
    "- Clinical vs patient language\n\n"
    "Return ONLY the alternative questions, one per line, without numbering or explanations.\n\n"
    "Original question: {question}\n\n"
    "Alternative questions:"
)


GREETING_RESPONSES = {
    "hi": "Hello! I'm your medical information assistant. You can ask me questions about medications, treatments, clinical studies, or any other medical topics. How can I help you today?",
    "hello": "Hello! I'm here to help with medical information and questions. What would you like to know about?",
    "hey": "Hi there! I'm your medical assistant. Feel free to ask me any medical questions you might have.",
    "thank": "You're welcome! Feel free to ask me any other medical questions you might have.",
    "thanks": "You're welcome! Is there anything else you'd like to know about?",
    "bye": "Goodbye! Take care, and don't hesitate to reach out if you have any medical questions in the future.",
    "okay": "Is there anything specific you'd like to know about? I can help with medical information, drug details, clinical studies, and more."
}

def is_greeting_or_casual(text: str) -> bool:
    """Check if the input is a greeting or casual interaction"""
    text = text.lower().strip()
    casual_patterns = [
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
        "how are you", "what's up", "sup", "greetings", "thank you", "thanks",
        "bye", "goodbye", "see you", "ok", "okay", "alright"
    ]
    
    # Check for exact matches or if query is very short
    return any(pattern in text for pattern in casual_patterns) or len(text.strip()) <= 3

def handle_greeting_or_casual(text: str) -> str:
    """Handle greetings and casual interactions"""
    text = text.lower().strip()
    
    for pattern, response in GREETING_RESPONSES.items():
        if pattern in text:
            return response
    
    return "I'm here to help with medical information. What would you like to know about?"

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

def generate_query_paraphrases(
    original_query: str,
    provider: Provider = "auto",
    model_override: Optional[str] = None,
) -> List[str]:
    """
    Generate paraphrases of the original query for multi-query retrieval
    """
    prompt = QUERY_REWRITING_PROMPT.format(question=original_query)
    
    try:
        response = generate_answer(
            prompt,
            provider=provider,
            model_override=model_override,
            temperature=0.7,  # Higher temperature for more diverse paraphrases
            max_tokens=200,
        )
        
        if response.startswith("[No LLM providers"):
            print("⚠️ No LLM available for query rewriting, using original query only")
            return [original_query]
        
        # Parse the response into individual questions
        paraphrases = []
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            # Remove numbering, bullets, or dashes
            line = re.sub(r'^[\d\.\-\*\•]\s*', '', line)
            if line and len(line) > 10:  # Only add substantial questions
                paraphrases.append(line)
        
        # Always include the original query
        all_queries = [original_query] + paraphrases
        
        # Limit to 5 total queries to avoid overwhelming the system
        return all_queries[:5]
        
    except Exception as e:
        print(f"Query rewriting failed: {e}")
        return [original_query]

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
