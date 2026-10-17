"""Build the gated AI client from settings.

The factory always returns a ``GatedLLMClient``, so callers cannot bypass the
guardrails by choosing an adapter directly. When AI is off it returns a gated
client with no provider inside: the master-switch gate raises before anything
else happens, and no key is required to build it.
"""
from __future__ import annotations

import httpx

from app.core.ai.client import GatedLLMClient, LLMClient
from app.core.ai.errors import AIUnavailableError
from app.core.ai.fake import FakeLLMClient
from app.core.ai.gemini import GeminiLLMClient
from app.core.ai.openai_compat import OpenAICompatLLMClient
from app.core.config import Settings


def get_llm_client(
    settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
) -> LLMClient:
    """Return the guardrail-wrapped AI client for the configured provider."""
    if not settings.AI_ENABLED:
        return GatedLLMClient(settings, None)

    provider = settings.AI_PROVIDER

    if provider == "fake":
        inner: LLMClient = FakeLLMClient()

    elif provider == "gemini":
        api_key = settings.GEMINI_API_KEY
        if api_key is None or not settings.AI_MODEL:
            raise AIUnavailableError("policy")
        # "default" means "do not send a level": the provider's own default stands.
        thinking_level = (
            None
            if settings.AI_THINKING_LEVEL == "default"
            else settings.AI_THINKING_LEVEL
        )
        inner = GeminiLLMClient(
            api_key=api_key.get_secret_value(),
            model=settings.AI_MODEL,
            max_output_tokens=settings.AI_MAX_OUTPUT_TOKENS,
            timeout_seconds=settings.AI_TIMEOUT_SECONDS,
            thinking_level=thinking_level,
            transport=transport,
        )

    elif provider == "openai_compatible":
        api_key = settings.AI_COMPAT_API_KEY
        if api_key is None or not settings.AI_COMPAT_BASE_URL or not settings.AI_MODEL:
            raise AIUnavailableError("policy")
        inner = OpenAICompatLLMClient(
            api_key=api_key.get_secret_value(),
            base_url=settings.AI_COMPAT_BASE_URL,
            model=settings.AI_MODEL,
            max_output_tokens=settings.AI_MAX_OUTPUT_TOKENS,
            timeout_seconds=settings.AI_TIMEOUT_SECONDS,
            transport=transport,
        )

    else:
        raise AIUnavailableError("policy")

    return GatedLLMClient(settings, inner)
