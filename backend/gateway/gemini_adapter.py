"""Sentinel Shield v2 — Google Gemini Adapter"""
import os
from typing import Dict, Any

try:
    import google.generativeai as genai
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class GeminiAdapter:
    def __init__(self):
        if not _AVAILABLE:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    def complete(self, prompt: str, context: str = "", system_prompt: str = "",
                 model: str = "gemini/gemini-1.5-pro", **kwargs) -> Dict[str, Any]:
        _, model_name = model.split("/", 1) if "/" in model else ("gemini", model)
        model_obj = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt or "You are a helpful assistant."
        )
        full_prompt = f"Context:\n{context}\n\nQuestion: {prompt}" if context else prompt
        resp = model_obj.generate_content(full_prompt)
        return {
            "answer": resp.text,
            "tokens_used": 0,  # Gemini SDK doesn't expose token count directly in all versions
        }
