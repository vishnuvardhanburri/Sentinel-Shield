"""
Sentinel Shield v2 — Multi-Model Gateway (Router)
Routes governed prompts to any AI model backend transparently.
Deployment modes:
  - AIRGAP: Ollama local models only
  - CLOUD:  OpenAI / Anthropic / Gemini via their APIs
  - HYBRID: Try cloud; fall back to Ollama if unavailable
"""
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("sentinel.gateway")

DEPLOYMENT_MODE = os.getenv("DEPLOYMENT_MODE", "airgap").lower()  # airgap | cloud | hybrid


class ModelRouter:
    """
    Unified model gateway. Accepts a governed (already-redacted) prompt
    and routes it to the appropriate backend.
    """

    DEFAULT_MODEL_MAP = {
        "airgap": "ollama/llama3.1",
        "cloud":  "openai/gpt-4o",
        "hybrid": "openai/gpt-4o",
    }

    def __init__(self):
        self.mode = DEPLOYMENT_MODE
        self._adapters: Dict[str, Any] = {}
        self._load_adapters()

    def _load_adapters(self):
        """Lazily load adapters based on deployment mode."""
        if self.mode in ("airgap", "hybrid"):
            try:
                from .ollama_adapter import OllamaAdapter
                self._adapters["ollama"] = OllamaAdapter()
            except ImportError:
                logger.warning("Ollama adapter unavailable")

        if self.mode in ("cloud", "hybrid"):
            if os.getenv("OPENAI_API_KEY"):
                try:
                    from .openai_adapter import OpenAIAdapter
                    self._adapters["openai"] = OpenAIAdapter()
                except ImportError:
                    logger.warning("OpenAI adapter unavailable")

            if os.getenv("ANTHROPIC_API_KEY"):
                try:
                    from .anthropic_adapter import AnthropicAdapter
                    self._adapters["anthropic"] = AnthropicAdapter()
                except ImportError:
                    logger.warning("Anthropic adapter unavailable")

            if os.getenv("GEMINI_API_KEY"):
                try:
                    from .gemini_adapter import GeminiAdapter
                    self._adapters["gemini"] = GeminiAdapter()
                except ImportError:
                    logger.warning("Gemini adapter unavailable")

            if os.getenv("OPENROUTER_API_KEY"):
                try:
                    from .openrouter_adapter import OpenRouterAdapter
                    self._adapters["openrouter"] = OpenRouterAdapter()
                except ImportError:
                    logger.warning("OpenRouter adapter unavailable")

    def route(
        self,
        prompt: str,
        preferred_model: Optional[str] = None,
        department: Optional[str] = None,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Route a governed prompt to the best available model.
        Returns: {answer, model_used, tokens_used, fallback_used}
        """
        target = preferred_model or self.DEFAULT_MODEL_MAP.get(self.mode, "ollama/llama3.1")
        provider, _ = self._parse_model(target)

        # Attempt primary
        adapter = self._adapters.get(provider)
        if adapter:
            try:
                result = adapter.complete(
                    prompt=prompt,
                    context=context or "",
                    system_prompt=system_prompt or self._default_system_prompt(),
                    model=target,
                )
                result["model_used"] = target
                result["fallback_used"] = False
                return result
            except Exception as e:
                logger.error(f"Primary adapter '{provider}' failed: {e}")

        # Fallback to Ollama in hybrid mode
        if self.mode == "hybrid" and "ollama" in self._adapters:
            try:
                logger.warning(f"Falling back to Ollama from {provider}")
                result = self._adapters["ollama"].complete(
                    prompt=prompt,
                    context=context or "",
                    system_prompt=system_prompt or self._default_system_prompt(),
                    model="ollama/llama3.1",
                )
                result["model_used"] = "ollama/llama3.1"
                result["fallback_used"] = True
                return result
            except Exception as e:
                logger.error(f"Fallback Ollama also failed: {e}")

        return {
            "answer": "⚠️ No AI model available. Check your DEPLOYMENT_MODE and API keys.",
            "model_used": "none",
            "fallback_used": False,
            "tokens_used": 0,
        }

    @staticmethod
    def _parse_model(model_str: str):
        """Parse 'provider/model-name' into (provider, model)."""
        parts = model_str.split("/", 1)
        if len(parts) == 2:
            return parts[0].lower(), parts[1]
        return "ollama", model_str

    @staticmethod
    def _default_system_prompt() -> str:
        return (
            "You are the Sentinel Shield Auditor — a secure, enterprise-grade AI assistant. "
            "All data provided to you has already been scanned and redacted for PII/PHI by "
            "Sentinel Shield v2. If you see [REDACTED_*] tokens, acknowledge them as blocked "
            "sensitive information. Provide accurate, professional responses for enterprise use. "
            "Never request or reconstruct redacted information."
        )

    def list_available(self) -> Dict[str, bool]:
        """Return which adapters are currently available."""
        return {name: True for name in self._adapters}


# Singleton
model_router = ModelRouter()
