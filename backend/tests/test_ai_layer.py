"""Tests for the optional AI assist layer (BATCH AI-1).

No real network is used: every adapter test drives an ``httpx.MockTransport``.
No database is touched; these are unit tests with fakes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from app.core.ai.client import DataClass, GatedLLMClient, validate_json_schema
from app.core.ai.errors import AIUnavailableError
from app.core.ai.fake import FakeLLMClient
from app.core.ai.factory import get_llm_client
from app.core.ai.gemini import GeminiLLMClient
from app.core.ai.openai_compat import OpenAICompatLLMClient
from app.core.config import Settings

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}, "note": {"type": "string"}},
    "required": ["ok"],
}


def make_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/valora_test",
        # >=32 chars: the SECRET_KEY validator only exempts ENVIRONMENT=development.
        "SECRET_KEY": "test-secret-not-for-production-0123456789",
        "AI_ENABLED": False,
        "AI_INSIGHTS_ENABLED": False,
        "AI_TRIAGE_ENABLED": False,
        "AI_PERSONAL_DATA_ALLOWED": False,
        "AI_PROVIDER": "fake",
        "AI_MODEL": "fake-model",
        "AI_TIMEOUT_SECONDS": 15.0,
        "AI_MAX_INPUT_CHARS": 6000,
        "AI_MAX_OUTPUT_TOKENS": 321,
        "GEMINI_API_KEY": None,
        "AI_COMPAT_BASE_URL": None,
        "AI_COMPAT_API_KEY": None,
    }
    base.update(overrides)
    return Settings(**base)


class CountingClient:
    """Test double recording how many times it was reached."""

    provider = "counting"
    model = "counting-model"

    def __init__(self) -> None:
        self.calls = 0

    async def generate_json(
        self, *, system, user, schema, data_class, feature
    ):  # type: ignore[no-untyped-def]
        self.calls += 1
        from app.core.ai.client import LLMResult

        return LLMResult(
            parsed={"ok": True},
            provider=self.provider,
            model=self.model,
            latency_ms=1,
            input_chars=len(system) + len(user),
        )


async def call(
    client,  # type: ignore[no-untyped-def]
    *,
    system: str = "system",
    user: str = "user",
    schema: dict[str, Any] | None = None,
    data_class: DataClass = DataClass.aggregate,
    feature: str = "insights",
):  # type: ignore[no-untyped-def]
    return await client.generate_json(
        system=system,
        user=user,
        schema=schema if schema is not None else SCHEMA,
        data_class=data_class,
        feature=feature,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------- master switch


@pytest.mark.asyncio
async def test_disabled_master_switch_blocks_before_any_http() -> None:
    settings = make_settings(AI_ENABLED=False, AI_INSIGHTS_ENABLED=True)
    inner = CountingClient()
    gated = GatedLLMClient(settings, inner)

    with pytest.raises(AIUnavailableError) as exc:
        await call(gated)

    assert exc.value.reason == "disabled"
    assert inner.calls == 0


@pytest.mark.asyncio
async def test_feature_flag_off_blocks_even_when_ai_enabled() -> None:
    settings = make_settings(AI_ENABLED=True, AI_INSIGHTS_ENABLED=False)
    inner = CountingClient()
    gated = GatedLLMClient(settings, inner)

    with pytest.raises(AIUnavailableError) as exc:
        await call(gated, feature="insights")
    assert exc.value.reason == "disabled"

    # The other feature has its own switch.
    settings2 = make_settings(AI_ENABLED=True, AI_TRIAGE_ENABLED=True)
    inner2 = CountingClient()
    gated2 = GatedLLMClient(settings2, inner2)
    result = await call(gated2, feature="triage")
    assert result.parsed == {"ok": True}
    assert inner2.calls == 1

    with pytest.raises(AIUnavailableError) as exc2:
        await call(gated2, feature="insights")
    assert exc2.value.reason == "disabled"


@pytest.mark.asyncio
async def test_personal_data_requires_explicit_opt_in() -> None:
    settings = make_settings(
        AI_ENABLED=True, AI_INSIGHTS_ENABLED=True, AI_PERSONAL_DATA_ALLOWED=False
    )
    inner = CountingClient()
    gated = GatedLLMClient(settings, inner)

    with pytest.raises(AIUnavailableError) as exc:
        await call(gated, data_class=DataClass.personal)

    assert exc.value.reason == "policy"
    assert inner.calls == 0


@pytest.mark.asyncio
async def test_personal_data_allowed_when_opted_in() -> None:
    settings = make_settings(
        AI_ENABLED=True, AI_INSIGHTS_ENABLED=True, AI_PERSONAL_DATA_ALLOWED=True
    )
    inner = CountingClient()
    gated = GatedLLMClient(settings, inner)

    result = await call(gated, data_class=DataClass.personal)
    assert result.parsed == {"ok": True}
    assert inner.calls == 1


@pytest.mark.asyncio
async def test_oversize_input_is_rejected_before_any_http() -> None:
    settings = make_settings(
        AI_ENABLED=True, AI_INSIGHTS_ENABLED=True, AI_MAX_INPUT_CHARS=50
    )
    inner = CountingClient()
    gated = GatedLLMClient(settings, inner)

    with pytest.raises(AIUnavailableError) as exc:
        await call(gated, system="s" * 40, user="u" * 40)

    assert exc.value.reason == "policy"
    assert inner.calls == 0


@pytest.mark.asyncio
async def test_exactly_max_input_chars_is_allowed() -> None:
    settings = make_settings(
        AI_ENABLED=True, AI_INSIGHTS_ENABLED=True, AI_MAX_INPUT_CHARS=20
    )
    inner = CountingClient()
    gated = GatedLLMClient(settings, inner)

    result = await call(gated, system="s" * 10, user="u" * 10)
    assert result.parsed == {"ok": True}
    assert inner.calls == 1


@pytest.mark.asyncio
async def test_gate_wrapper_enforces_a_hard_timeout_with_no_retry() -> None:
    class SlowClient:
        provider = "slow"
        model = "slow-model"

        def __init__(self) -> None:
            self.calls = 0

        async def generate_json(self, **kwargs: Any):  # type: ignore[no-untyped-def]
            self.calls += 1
            await asyncio.sleep(5)
            raise AssertionError("should have been cancelled")

    settings = make_settings(
        AI_ENABLED=True, AI_INSIGHTS_ENABLED=True, AI_TIMEOUT_SECONDS=0.05
    )
    inner = SlowClient()
    gated = GatedLLMClient(settings, inner)

    with pytest.raises(AIUnavailableError) as exc:
        await call(gated)

    assert exc.value.reason == "timeout"
    assert inner.calls == 1


# ------------------------------------------------------------- gemini adapter


def gemini_transport(
    *, status_code: int = 200, body: Any = None, capture: dict[str, Any] | None = None,
    delay: float = 0.0,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture["url"] = str(request.url)
            capture["headers"] = dict(request.headers)
            capture["body"] = json.loads(request.content.decode("utf-8"))
            capture["calls"] = capture.get("calls", 0) + 1
        if delay:
            import time as _time

            _time.sleep(delay)
        if body is None:
            return httpx.Response(status_code, text="not json at all")
        return httpx.Response(status_code, json=body)

    return httpx.MockTransport(handler)


def gemini_ok_body(text: str) -> dict[str, Any]:
    return {
        "id": "v1_test",
        "object": "interaction",
        "model": "gemini-test-model",
        "status": "completed",
        "steps": [
            {"type": "model_output", "content": [{"type": "text", "text": text}]}
        ],
    }


def gemini_incomplete_body() -> dict[str, Any]:
    """What the provider returns when the output budget ran out mid-thought.

    Observed verbatim against gemini-3.8-flash: HTTP 200, ``status``
    ``incomplete``, a handful of output tokens, hundreds of *thought* tokens and
    no text at all. Thinking counts against ``max_output_tokens``, so an
    undersized cap produces exactly this.
    """
    return {
        "id": "v1_test",
        "object": "interaction",
        "model": "gemini-test-model",
        "status": "incomplete",
        "usage": {
            "total_output_tokens": 9,
            "total_thought_tokens": 577,
        },
        "steps": [],
    }


def make_gemini(**overrides: Any) -> GeminiLLMClient:
    kwargs: dict[str, Any] = {
        "api_key": "test-gemini-key",
        "model": "gemini-test-model",
        "max_output_tokens": 321,
        "timeout_seconds": 15.0,
        "transport": gemini_transport(body=gemini_ok_body('{"ok": true}')),
    }
    kwargs.update(overrides)
    return GeminiLLMClient(**kwargs)


@pytest.mark.asyncio
async def test_gemini_adapter_parses_schema_valid_output() -> None:
    client = make_gemini()
    result = await call(client)

    assert result.parsed == {"ok": True}
    assert result.provider == "gemini"
    assert result.model == "gemini-test-model"
    assert result.input_chars == len("system") + len("user")
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_compat_answer_cut_off_at_the_token_limit_raises_truncated() -> None:
    """``finish_reason: length`` is an exhausted budget, not a bad answer."""
    body = compat_ok_body('{"ok": tr')
    body["choices"][0]["finish_reason"] = "length"
    client = make_compat(transport=compat_transport(body=body))

    with pytest.raises(AIUnavailableError) as exc:
        await call(client)
    assert exc.value.reason == "truncated"


@pytest.mark.asyncio
async def test_compat_answer_cut_off_with_no_content_raises_truncated() -> None:
    body = compat_ok_body("")
    body["choices"][0]["finish_reason"] = "length"
    client = make_compat(transport=compat_transport(body=body))

    with pytest.raises(AIUnavailableError) as exc:
        await call(client)
    assert exc.value.reason == "truncated"


@pytest.mark.asyncio
async def test_compat_complete_answer_at_the_token_limit_is_still_used() -> None:
    """A finished, valid answer is never thrown away for being at the limit."""
    body = compat_ok_body('{"ok": true}')
    body["choices"][0]["finish_reason"] = "length"
    client = make_compat(transport=compat_transport(body=body))

    result = await call(client)
    assert result.parsed == {"ok": True}


@pytest.mark.asyncio
async def test_gemini_incomplete_interaction_raises_truncated() -> None:
    """An exhausted output budget is not a malformed answer and must say so."""
    client = make_gemini(transport=gemini_transport(body=gemini_incomplete_body()))

    with pytest.raises(AIUnavailableError) as exc:
        await call(client)
    assert exc.value.reason == "truncated"


@pytest.mark.asyncio
async def test_gemini_completed_interaction_without_text_raises_invalid_output() -> None:
    """A finished interaction with no text is a provider contract failure."""
    body = gemini_incomplete_body()
    body["status"] = "completed"
    client = make_gemini(transport=gemini_transport(body=body))

    with pytest.raises(AIUnavailableError) as exc:
        await call(client)
    assert exc.value.reason == "invalid_output"


@pytest.mark.asyncio
async def test_gemini_sends_the_configured_thinking_level() -> None:
    capture: dict[str, Any] = {}
    client = make_gemini(
        thinking_level="low",
        transport=gemini_transport(body=gemini_ok_body('{"ok": true}'), capture=capture),
    )
    await call(client)

    assert capture["body"]["generation_config"]["thinking_level"] == "low"


@pytest.mark.asyncio
async def test_gemini_omits_thinking_level_when_it_is_not_configured() -> None:
    capture: dict[str, Any] = {}
    client = make_gemini(
        transport=gemini_transport(body=gemini_ok_body('{"ok": true}'), capture=capture)
    )
    await call(client)

    assert "thinking_level" not in capture["body"]["generation_config"]


@pytest.mark.asyncio
async def test_gemini_request_shape_matches_current_docs() -> None:
    capture: dict[str, Any] = {}
    client = make_gemini(
        transport=gemini_transport(body=gemini_ok_body('{"ok": true}'), capture=capture)
    )
    await call(client, system="sys", user="usr")

    assert capture["url"] == "https://generativelanguage.googleapis.com/v1beta/interactions"

    headers = {k.lower(): v for k, v in capture["headers"].items()}
    assert headers["x-goog-api-key"] == "test-gemini-key"
    assert "authorization" not in headers

    body = capture["body"]
    assert body["model"] == "gemini-test-model"
    assert body["input"] == "usr"
    assert body["system_instruction"] == "sys"
    assert body["response_format"]["mime_type"] == "application/json"
    assert body["response_format"]["schema"] == SCHEMA
    assert body["generation_config"]["max_output_tokens"] == 321
    # Privacy: we never let the provider retain the interaction.
    assert body["store"] is False


# ------------------------------------------------------ openai-compatible adapter


def compat_transport(
    *, status_code: int = 200, body: Any = None, capture: dict[str, Any] | None = None
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture["url"] = str(request.url)
            capture["headers"] = dict(request.headers)
            capture["body"] = json.loads(request.content.decode("utf-8"))
            capture["calls"] = capture.get("calls", 0) + 1
        if body is None:
            return httpx.Response(status_code, text="not json at all")
        return httpx.Response(status_code, json=body)

    return httpx.MockTransport(handler)


def compat_ok_body(text: str) -> dict[str, Any]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "compat-test-model",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": text}}
        ],
    }


def make_compat(**overrides: Any) -> OpenAICompatLLMClient:
    kwargs: dict[str, Any] = {
        "api_key": "test-compat-key",
        "base_url": "https://integrate.example.com/v1",
        "model": "compat-test-model",
        "max_output_tokens": 321,
        "timeout_seconds": 15.0,
        "transport": compat_transport(body=compat_ok_body('{"ok": true}')),
    }
    kwargs.update(overrides)
    return OpenAICompatLLMClient(**kwargs)


@pytest.mark.asyncio
async def test_openai_compatible_adapter_parses_schema_valid_output() -> None:
    client = make_compat()
    result = await call(client)

    assert result.parsed == {"ok": True}
    assert result.provider == "openai_compatible"


@pytest.mark.asyncio
async def test_openai_compatible_request_shape() -> None:
    capture: dict[str, Any] = {}
    client = make_compat(
        transport=compat_transport(body=compat_ok_body('{"ok": true}'), capture=capture)
    )
    await call(client, system="sys", user="usr")

    assert capture["url"] == "https://integrate.example.com/v1/chat/completions"

    headers = {k.lower(): v for k, v in capture["headers"].items()}
    assert headers["authorization"] == "Bearer test-compat-key"

    body = capture["body"]
    assert body["model"] == "compat-test-model"
    assert body["response_format"] == {"type": "json_object"}
    assert body["max_tokens"] == 321
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["system", "user"]
    assert body["messages"][1]["content"] == "usr"
    # OpenAI's JSON mode requires the literal word "json" in the messages.
    assert "json" in body["messages"][0]["content"].lower()


@pytest.mark.asyncio
async def test_openai_compatible_base_url_without_v1_suffix() -> None:
    capture: dict[str, Any] = {}
    client = make_compat(
        base_url="https://integrate.example.com",
        transport=compat_transport(body=compat_ok_body('{"ok": true}'), capture=capture),
    )
    await call(client)
    assert capture["url"] == "https://integrate.example.com/v1/chat/completions"


# ------------------------------------------------------------- failure mapping


@pytest.mark.parametrize(
    ("status_code", "reason"),
    [
        (401, "provider_error"),
        (403, "provider_error"),
        (500, "provider_error"),
        (503, "provider_error"),
        # A spent quota is not a broken key or a bug: it is a limit, and an
        # operator has to be able to tell the two apart from the reason code.
        (429, "rate_limited"),
    ],
)
@pytest.mark.parametrize("adapter", ["gemini", "compat"])
@pytest.mark.asyncio
async def test_http_error_statuses_raise_ai_unavailable(
    adapter: str, status_code: int, reason: str
) -> None:
    if adapter == "gemini":
        client = make_gemini(
            transport=gemini_transport(status_code=status_code, body={"error": "nope"})
        )
    else:
        client = make_compat(
            transport=compat_transport(status_code=status_code, body={"error": "nope"})
        )

    with pytest.raises(AIUnavailableError) as exc:
        await call(client)
    assert exc.value.reason == reason


@pytest.mark.parametrize("adapter", ["gemini", "compat"])
@pytest.mark.asyncio
async def test_non_json_body_raises_invalid_output(adapter: str) -> None:
    if adapter == "gemini":
        client = make_gemini(transport=gemini_transport(body=None))
    else:
        client = make_compat(transport=compat_transport(body=None))

    with pytest.raises(AIUnavailableError) as exc:
        await call(client)
    assert exc.value.reason == "invalid_output"


@pytest.mark.parametrize("adapter", ["gemini", "compat"])
@pytest.mark.asyncio
async def test_wrong_schema_output_raises_invalid_output(adapter: str) -> None:
    if adapter == "gemini":
        client = make_gemini(
            transport=gemini_transport(body=gemini_ok_body('{"note": "no ok field"}'))
        )
    else:
        client = make_compat(
            transport=compat_transport(body=compat_ok_body('{"note": "no ok field"}'))
        )

    with pytest.raises(AIUnavailableError) as exc:
        await call(client)
    assert exc.value.reason == "invalid_output"


@pytest.mark.parametrize("adapter", ["gemini", "compat"])
@pytest.mark.asyncio
async def test_non_object_json_output_raises_invalid_output(adapter: str) -> None:
    if adapter == "gemini":
        client = make_gemini(transport=gemini_transport(body=gemini_ok_body("[1, 2, 3]")))
    else:
        client = make_compat(transport=compat_transport(body=compat_ok_body("[1, 2, 3]")))

    with pytest.raises(AIUnavailableError) as exc:
        await call(client)
    assert exc.value.reason == "invalid_output"


@pytest.mark.asyncio
async def test_transport_timeout_raises_timeout_reason() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    client = make_gemini(transport=httpx.MockTransport(handler))
    with pytest.raises(AIUnavailableError) as exc:
        await call(client)
    assert exc.value.reason == "timeout"


@pytest.mark.asyncio
async def test_transport_connect_error_raises_network_reason() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    client = make_gemini(transport=httpx.MockTransport(handler))
    with pytest.raises(AIUnavailableError) as exc:
        await call(client)
    assert exc.value.reason == "network"


@pytest.mark.asyncio
async def test_adapter_does_not_retry_a_failed_call() -> None:
    capture: dict[str, Any] = {}
    client = make_gemini(
        transport=gemini_transport(
            status_code=500, body={"error": "boom"}, capture=capture
        )
    )

    with pytest.raises(AIUnavailableError):
        await call(client)

    assert capture["calls"] == 1


# ------------------------------------------------------------- secret hygiene


@pytest.mark.asyncio
async def test_keys_never_appear_in_settings_repr_exceptions_or_logs(caplog) -> None:
    secret = "super-secret-gemini-key-value"
    settings = make_settings(
        AI_ENABLED=True,
        AI_INSIGHTS_ENABLED=True,
        AI_PROVIDER="gemini",
        AI_MODEL="gemini-test-model",
        GEMINI_API_KEY=secret,
    )

    assert secret not in repr(settings)
    assert secret not in str(settings)

    client = make_gemini(
        api_key=secret, transport=gemini_transport(status_code=401, body={"error": "x"})
    )
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(AIUnavailableError) as exc:
            await call(client)

    assert secret not in str(exc.value)
    assert secret not in repr(exc.value)
    assert secret not in caplog.text


@pytest.mark.asyncio
async def test_provider_error_message_does_not_echo_provider_body() -> None:
    client = make_gemini(
        transport=gemini_transport(
            status_code=500, body={"error": "leak this personal data"}
        )
    )
    with pytest.raises(AIUnavailableError) as exc:
        await call(client)
    assert "leak this personal data" not in str(exc.value)


# ------------------------------------------------------------- config validation


def test_shipped_ai_defaults_allow_a_gemini_brief_to_complete() -> None:
    """Leave room for reasoning and for the measured provider latency.

    600 was the old default and it was spent on thoughts: the interaction came
    back ``incomplete`` with no text, which surfaced as ``invalid_output``.
    Gemini also took 55 seconds for one brief; a 15-second cap timed out first.
    """
    assert Settings.model_fields["AI_MAX_OUTPUT_TOKENS"].default >= 2048
    assert Settings.model_fields["AI_THINKING_LEVEL"].default == "low"
    assert Settings.model_fields["AI_TIMEOUT_SECONDS"].default == 75.0


def test_thinking_level_accepts_the_documented_levels_and_a_provider_default() -> None:
    for level in ("minimal", "low", "medium", "high", "default"):
        assert make_settings(AI_THINKING_LEVEL=level).AI_THINKING_LEVEL == level

    with pytest.raises(ValidationError):
        make_settings(AI_THINKING_LEVEL="enormous")


def test_ai_enabled_requires_gemini_key_and_model() -> None:
    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        make_settings(AI_ENABLED=True, AI_PROVIDER="gemini", GEMINI_API_KEY=None, AI_MODEL="m")

    with pytest.raises(ValidationError, match="AI_MODEL"):
        make_settings(
            AI_ENABLED=True, AI_PROVIDER="gemini", GEMINI_API_KEY="k", AI_MODEL=None
        )


def test_openai_compatible_provider_requires_base_url_and_key() -> None:
    with pytest.raises(ValidationError, match="AI_COMPAT_BASE_URL"):
        make_settings(
            AI_ENABLED=True,
            AI_PROVIDER="openai_compatible",
            AI_MODEL="m",
            AI_COMPAT_API_KEY="k",
            AI_COMPAT_BASE_URL=None,
        )

    with pytest.raises(ValidationError, match="AI_COMPAT_API_KEY"):
        make_settings(
            AI_ENABLED=True,
            AI_PROVIDER="openai_compatible",
            AI_MODEL="m",
            AI_COMPAT_BASE_URL="https://example.com/v1",
            AI_COMPAT_API_KEY=None,
        )


def test_fake_provider_refused_outside_development_and_test() -> None:
    with pytest.raises(ValidationError, match="fake"):
        make_settings(ENVIRONMENT="production", AI_PROVIDER="fake")

    with pytest.raises(ValidationError, match="fake"):
        make_settings(ENVIRONMENT="staging", AI_ENABLED=True, AI_PROVIDER="fake")

    # Allowed in development and test.
    assert make_settings(ENVIRONMENT="development", AI_PROVIDER="fake").AI_PROVIDER == "fake"
    assert make_settings(ENVIRONMENT="test", AI_PROVIDER="fake").AI_PROVIDER == "fake"


def test_personal_data_flag_requires_ai_enabled() -> None:
    with pytest.raises(ValidationError, match="AI_PERSONAL_DATA_ALLOWED"):
        make_settings(AI_ENABLED=False, AI_PERSONAL_DATA_ALLOWED=True)


def test_unknown_provider_is_refused() -> None:
    with pytest.raises(ValidationError):
        make_settings(AI_PROVIDER="wat")


def test_ai_defaults_are_all_off() -> None:
    settings = make_settings()
    assert settings.AI_ENABLED is False
    assert settings.AI_INSIGHTS_ENABLED is False
    assert settings.AI_TRIAGE_ENABLED is False
    assert settings.AI_PERSONAL_DATA_ALLOWED is False


# ------------------------------------------------------------------- factory


def test_factory_returns_gated_client_with_no_provider_when_disabled() -> None:
    settings = make_settings(AI_ENABLED=False)
    client = get_llm_client(settings)
    assert isinstance(client, GatedLLMClient)
    assert client.inner is None


def test_factory_builds_fake_provider() -> None:
    settings = make_settings(AI_ENABLED=True, AI_PROVIDER="fake", AI_INSIGHTS_ENABLED=True)
    client = get_llm_client(settings)
    assert isinstance(client.inner, FakeLLMClient)


@pytest.mark.asyncio
async def test_factory_passes_max_output_tokens_to_the_gemini_provider() -> None:
    capture: dict[str, Any] = {}
    settings = make_settings(
        AI_ENABLED=True,
        AI_INSIGHTS_ENABLED=True,
        AI_PROVIDER="gemini",
        AI_MODEL="gemini-test-model",
        GEMINI_API_KEY="test-gemini-key",
        AI_MAX_OUTPUT_TOKENS=777,
    )
    client = get_llm_client(
        settings, transport=gemini_transport(body=gemini_ok_body('{"ok": true}'), capture=capture)
    )

    result = await call(client)
    assert result.parsed == {"ok": True}
    assert capture["body"]["generation_config"]["max_output_tokens"] == 777


@pytest.mark.asyncio
async def test_factory_passes_the_thinking_level_to_the_gemini_provider() -> None:
    capture: dict[str, Any] = {}
    settings = make_settings(
        AI_ENABLED=True,
        AI_INSIGHTS_ENABLED=True,
        AI_PROVIDER="gemini",
        AI_MODEL="gemini-test-model",
        GEMINI_API_KEY="test-gemini-key",
        AI_THINKING_LEVEL="low",
    )
    client = get_llm_client(
        settings, transport=gemini_transport(body=gemini_ok_body('{"ok": true}'), capture=capture)
    )
    await call(client)

    assert capture["body"]["generation_config"]["thinking_level"] == "low"


@pytest.mark.asyncio
async def test_factory_leaves_thinking_to_the_provider_when_level_is_default() -> None:
    capture: dict[str, Any] = {}
    settings = make_settings(
        AI_ENABLED=True,
        AI_INSIGHTS_ENABLED=True,
        AI_PROVIDER="gemini",
        AI_MODEL="gemini-test-model",
        GEMINI_API_KEY="test-gemini-key",
        AI_THINKING_LEVEL="default",
    )
    client = get_llm_client(
        settings, transport=gemini_transport(body=gemini_ok_body('{"ok": true}'), capture=capture)
    )
    await call(client)

    assert "thinking_level" not in capture["body"]["generation_config"]


@pytest.mark.asyncio
async def test_factory_gemini_end_to_end_through_gates() -> None:
    settings = make_settings(
        AI_ENABLED=True,
        AI_INSIGHTS_ENABLED=True,
        AI_PROVIDER="gemini",
        AI_MODEL="gemini-test-model",
        GEMINI_API_KEY="test-gemini-key",
    )
    client = get_llm_client(
        settings, transport=gemini_transport(body=gemini_ok_body('{"ok": true}'))
    )
    result = await call(client)
    assert result.parsed == {"ok": True}
    assert result.provider == "gemini"


# ---------------------------------------------------------------------- fake


@pytest.mark.asyncio
async def test_fake_client_is_deterministic_and_schema_valid() -> None:
    settings = make_settings(AI_ENABLED=True, AI_PROVIDER="fake", AI_INSIGHTS_ENABLED=True)
    client = get_llm_client(settings)

    first = await call(client, schema=SCHEMA)
    second = await call(client, schema=SCHEMA)

    assert first.parsed == second.parsed
    assert isinstance(first.parsed, dict)
    assert first.parsed.get("ok") is True
    validate_json_schema(first.parsed, SCHEMA)


@pytest.mark.asyncio
async def test_fake_client_honours_an_explicit_response() -> None:
    settings = make_settings(AI_ENABLED=True, AI_PROVIDER="fake", AI_INSIGHTS_ENABLED=True)
    client = GatedLLMClient(settings, FakeLLMClient(response={"ok": False}))
    result = await call(client)
    assert result.parsed == {"ok": False}


def test_fake_client_provider_name_is_stable() -> None:
    client = FakeLLMClient()
    assert client.provider == "fake"
    assert client.model


# ----------------------------------------------------------- schema validator


def test_schema_validator_accepts_valid_nested_payload() -> None:
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "count": {"type": "integer"}},
            "required": ["name", "count"],
        },
    }
    validate_json_schema([{"name": "a", "count": 2}], schema)


def test_schema_validator_rejects_wrong_types_without_echoing_values() -> None:
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}

    with pytest.raises(AIUnavailableError) as exc:
        validate_json_schema({"ok": "personal-value-should-not-leak"}, schema)

    assert exc.value.reason == "invalid_output"
    assert "personal-value-should-not-leak" not in str(exc.value)


def test_schema_validator_rejects_missing_required_property() -> None:
    with pytest.raises(AIUnavailableError):
        validate_json_schema({}, SCHEMA)


def test_schema_validator_enforces_enums() -> None:
    schema = {"type": "string", "enum": ["low", "high"]}
    validate_json_schema("low", schema)
    with pytest.raises(AIUnavailableError):
        validate_json_schema("medium", schema)


def test_schema_validator_enforces_array_length_bounds() -> None:
    """``maxItems``/``minItems`` are part of the subset we ask providers for."""
    schema = {
        "type": "object",
        "properties": {
            "drivers": {"type": "array", "items": {"type": "string"}, "maxItems": 3, "minItems": 1}
        },
        "required": ["drivers"],
    }

    validate_json_schema({"drivers": ["a", "b", "c"]}, schema)

    with pytest.raises(AIUnavailableError) as too_many:
        validate_json_schema({"drivers": ["a", "b", "c", "d"]}, schema)
    assert too_many.value.reason == "invalid_output"

    with pytest.raises(AIUnavailableError) as too_few:
        validate_json_schema({"drivers": []}, schema)
    assert too_few.value.reason == "invalid_output"


# --------------------------------------------------------------- error object


def test_ai_unavailable_error_rejects_unknown_reason() -> None:
    with pytest.raises(ValueError):
        AIUnavailableError("not-a-reason")


def test_ai_unavailable_error_exposes_its_reason() -> None:
    assert AIUnavailableError("budget").reason == "budget"
