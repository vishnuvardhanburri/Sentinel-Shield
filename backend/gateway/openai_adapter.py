"""Sovereign Shield v2 — OpenAI Adapter"""
import os
from typing import Dict, Any

try:
    from openai import OpenAI
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class OpenAIAdapter:
    def __init__(self):
        if not _AVAILABLE:
            raise ImportError("openai package not installed. Run: pip install openai")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def complete(self, prompt: str, context: str = "", system_prompt: str = "",
                 model: str = "openai/gpt-4o", **kwargs) -> Dict[str, Any]:
        _, model_name = model.split("/", 1) if "/" in model else ("openai", model)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {prompt}"})
        else:
            messages.append({"role": "user", "content": prompt})

        resp = self.client.chat.completions.create(model=model_name, messages=messages)
        return {
            "answer": resp.choices[0].message.content,
            "tokens_used": resp.usage.total_tokens if resp.usage else 0,
        }
