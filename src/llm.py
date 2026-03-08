"""Shared Gemini client for CleanApp Agent001."""

from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import types

from .config import Config

logger = logging.getLogger(__name__)

_PROFILE_BUDGETS = {
    "none": 0,
    "light": 4096,
    "high": 24576,
}


class GeminiLLM:
    """Thin wrapper around the Google GenAI SDK with optional fallback model."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        fallback_model: str | None = None,
        reasoning_profile: str = "light",
        thinking_budget: int | None = None,
    ):
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.fallback_model = fallback_model or None
        self.reasoning_profile = reasoning_profile.strip().lower() or "light"
        self.thinking_budget = thinking_budget

    @classmethod
    def from_config(cls, config: Config) -> "GeminiLLM":
        return cls(
            api_key=config.gemini_api_key,
            model=config.gemini_model,
            fallback_model=config.gemini_fallback_model,
            reasoning_profile=config.gemini_reasoning_profile,
            thinking_budget=config.gemini_thinking_budget,
        )

    def generate_text(self, prompt: str) -> str:
        """Generate plain text from the primary model, with optional fallback."""
        last_error: Exception | None = None
        for model in self._models():
            try:
                return self._generate_with_model(model, prompt)
            except Exception as exc:  # pragma: no cover - SDK/network dependent
                last_error = exc
                logger.error("Gemini generation failed on model %s: %s", model, exc)
        if last_error is not None:
            raise last_error
        raise RuntimeError("No Gemini model configured")

    def _models(self) -> list[str]:
        models = [self.model]
        if self.fallback_model and self.fallback_model != self.model:
            models.append(self.fallback_model)
        return models

    def _generate_with_model(self, model: str, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=self._generation_config(model),
        )
        text = self._extract_text(response)
        if not text:
            raise RuntimeError(f"Gemini returned empty text for model {model}")
        return text.strip()

    def _generation_config(self, model: str) -> types.GenerateContentConfig | None:
        budget = self._effective_thinking_budget()
        if budget is None:
            return None
        if not self._supports_thinking_budget(model):
            return None
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                includeThoughts=False,
                thinkingBudget=budget,
            )
        )

    def _effective_thinking_budget(self) -> int | None:
        if self.thinking_budget is not None:
            return self.thinking_budget
        return _PROFILE_BUDGETS.get(self.reasoning_profile, _PROFILE_BUDGETS["light"])

    @staticmethod
    def _supports_thinking_budget(model: str) -> bool:
        lower = model.lower()
        return lower.startswith("gemini-3") or lower.startswith("gemini-2.5")

    @staticmethod
    def _extract_text(response: Any) -> str:
        text = getattr(response, "text", None)
        if text:
            return text

        chunks: list[str] = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            if not content:
                continue
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", None)
                if part_text:
                    chunks.append(part_text)
        return "\n".join(chunks).strip()
