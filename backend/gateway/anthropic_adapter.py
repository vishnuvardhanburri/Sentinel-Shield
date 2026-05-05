"""Sovereign Shield v2 — Anthropic (Claude) Adapter"""
import os
from typing import Dict, Any

try:
    import anthropic
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class AnthropicAdapter:
    def __init__(self):
        if not _AVAILABLE:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def complete(self, prompt: str, context: str = "", system_prompt: str = "",
                 model: str = "anthropic/claude-3-5-sonnet-20241022", **kwargs) -> Dict[str, Any]:
        _, model_name = model.split("/", 1) if "/" in model else ("anthropic", model)
        user_content = f"Context:\n{context}\n\nQuestion: {prompt}" if context else prompt

        resp = self.client.messages.create(
            model=model_name,
            max_tokens=2048,
            system=system_prompt or "You are a helpful assistant.",
            messages=[{"role": "user", "content": user_content}],
        )
        return {
            "answer": resp.content[0].text,
            "tokens_used": (resp.usage.input_tokens or 0) + (resp.usage.output_tokens or 0),
        }
