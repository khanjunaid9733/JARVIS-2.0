from __future__ import annotations

"""Module 6 OpenAI-compatible adapter tests. Offline: httpx.MockTransport only."""

import json

import httpx
import pytest

from jarvis.kernel.model_gateway import ProviderTransportError
from jarvis.providers.openai_compatible import OpenAICompatibleAdapter

pytestmark = pytest.mark.anyio

API_KEY = "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"
BASE_URL = "https://api.groq.com/openai/v1"


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("JARVIS_MODEL_API_KEY", API_KEY)
    monkeypatch.setenv("JARVIS_MODEL_BASE_URL", BASE_URL)


def _chat_response(content: str, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        json={
            "choices": [{"message": {"role": "assistant", "content": content}}]
        },
    )


def _models_response(status: int = 200) -> httpx.Response:
    return httpx.Response(status_code=status, json={"data": []})


# ---------------------------------------------------------------------------
# Construction / env
# ---------------------------------------------------------------------------

def test_missing_env_at_construction_typed_failure(monkeypatch):
    monkeypatch.delenv("JARVIS_MODEL_API_KEY", raising=False)
    monkeypatch.delenv("JARVIS_MODEL_BASE_URL", raising=False)

    with pytest.raises(ProviderTransportError) as exc:
        OpenAICompatibleAdapter()

    assert "JARVIS_MODEL_API_KEY" in str(exc.value)
    assert "JARVIS_MODEL_BASE_URL" in str(exc.value)


def test_missing_key_only(monkeypatch):
    monkeypatch.delenv("JARVIS_MODEL_API_KEY", raising=False)
    monkeypatch.setenv("JARVIS_MODEL_BASE_URL", BASE_URL)

    with pytest.raises(ProviderTransportError) as exc:
        OpenAICompatibleAdapter()

    assert "JARVIS_MODEL_API_KEY" in str(exc.value)


def test_construction_reads_env(env):
    adapter = OpenAICompatibleAdapter()
    assert adapter._api_key == API_KEY  # noqa: SLF001
    assert adapter._base_url == BASE_URL  # noqa: SLF001


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

def test_structurally_conforms_to_provider_adapter(env):
    adapter = OpenAICompatibleAdapter()
    assert isinstance(adapter.provider_id, str)
    assert callable(getattr(adapter, "invoke"))
    assert callable(getattr(adapter, "health_check"))


# ---------------------------------------------------------------------------
# invoke
# ---------------------------------------------------------------------------

async def test_invoke_returns_dict_on_mocked_200(env):
    transport = httpx.MockTransport(
        lambda request: _chat_response(json.dumps({"text": "ok", "n": 3}))
    )
    adapter = OpenAICompatibleAdapter(transport=transport)

    result = await adapter.invoke(
        "model.generate_structured",
        "1.0.0",
        {"schema_id": "note", "schema_json": {"type": "object"}},
    )

    assert result == {"text": "ok", "n": 3}


async def test_invoke_maps_http_5xx_to_typed_transport_error(env):
    transport = httpx.MockTransport(lambda request: _chat_response("", status=500))
    adapter = OpenAICompatibleAdapter(transport=transport)

    with pytest.raises(ProviderTransportError) as exc:
        await adapter.invoke(
            "model.generate_structured",
            "1.0.0",
            {"schema_id": "note", "schema_json": {"type": "object"}},
        )

    assert "500" in str(exc.value)


async def test_invoke_rejects_non_json_content(env):
    transport = httpx.MockTransport(
        lambda request: _chat_response("not-json", status=200)
    )
    adapter = OpenAICompatibleAdapter(transport=transport)

    with pytest.raises(ProviderTransportError):
        await adapter.invoke(
            "model.generate_structured",
            "1.0.0",
            {"schema_id": "note", "schema_json": {"type": "object"}},
        )


async def test_invoke_rejects_missing_schema_json(env):
    transport = httpx.MockTransport(lambda request: _chat_response("{}"))
    adapter = OpenAICompatibleAdapter(transport=transport)

    with pytest.raises(ProviderTransportError):
        await adapter.invoke("model.generate_structured", "1.0.0", {})


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------

def test_health_check_true_on_200(env):
    transport = httpx.MockTransport(
        lambda request: _models_response(status=200)
    )
    adapter = OpenAICompatibleAdapter(transport=transport)

    assert adapter.health_check() is True


def test_health_check_false_on_500(env):
    transport = httpx.MockTransport(
        lambda request: _models_response(status=500)
    )
    adapter = OpenAICompatibleAdapter(transport=transport)

    assert adapter.health_check() is False


# ---------------------------------------------------------------------------
# Secrecy
# ---------------------------------------------------------------------------

def test_api_key_never_in_captured_logs(env, caplog):
    transport = httpx.MockTransport(
        lambda request: _chat_response(json.dumps({"text": "ok"}))
    )
    adapter = OpenAICompatibleAdapter(transport=transport)

    import asyncio

    asyncio.run(
        adapter.invoke(
            "model.generate_structured",
            "1.0.0",
            {"schema_id": "note", "schema_json": {"type": "object"}},
        )
    )

    assert API_KEY not in caplog.text