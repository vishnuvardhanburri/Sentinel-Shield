"""Sovereign Shield v2 — Ollama (Local) Adapter"""
import os
from typing import Dict, Any

try:
    from langchain_ollama import OllamaLLM
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class OllamaAdapter:
    def __init__(self):
        if not _AVAILABLE:
            raise ImportError("langchain-ollama not installed")
        self._models: Dict[str, OllamaLLM] = {}

    def _get_model(self, model_name: str) -> OllamaLLM:
        if model_name not in self._models:
            self._models[model_name] = OllamaLLM(model=model_name, base_url=OLLAMA_BASE)
        return self._models[model_name]

    def complete(self, prompt: str, context: str = "", system_prompt: str = "",
                 model: str = "ollama/llama3.1", **kwargs) -> Dict[str, Any]:
        _, model_name = model.split("/", 1) if "/" in model else ("ollama", model)
        llm = self._get_model(model_name)

        full_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nQuestion: {prompt}" if context else \
                      f"{system_prompt}\n\nQuestion: {prompt}"

        answer = llm.invoke(full_prompt)
        return {"answer": answer, "tokens_used": 0}
