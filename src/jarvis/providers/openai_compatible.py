from __future__ import annotations

"""OpenAI-compatible adapter for the Groq backend (module 6).

Implements the `ProviderAdapter` Protocol from `jarvis.kernel.registry`
(ADR-001). Talks to an OpenAI-compatible `/chat/completions` endpoint,
reads credentials from env AT CONSTRUCTION, and maps transport failures to
`ProviderTransportError` (defined in `jarvis.kernel.model_gateway`).

Design decisions (disclosed):
- Path: `jarvis/providers/openai_compatible.py` (adapters live under
  `jarvis.providers`, not the kernel).
- No LiteLLM in module 6 (spec §131.11 names it as the M1 routing
  implementation; with a single Groq route a direct OpenAI-compatible call
  satisfies ADR-001, and LiteLLM can be swapped in later as a different
  adapter behind the same Protocol — disclosed in the module report).
- Audio/session/etc. complexity deferred; this adapter covers
  `model.generate_structured` (SCHEMA_CONSTRAINED) only.
- Missing env vars at construction raise provider transport error (typed),
  never KeyError/AttributeError. The exact key is never logged.
"""

import json
import os
from typing import Any

import httpx

from jarvis.kernel.model_gateway import ProviderTransportError
from jarvis.kernel.registry import ProviderAdapter


class OpenAICompatibleAdapter:
    """ProviderAdapter for any OpenAI-compatible chat endpoint (e.g., Groq).

    Reads `JARVIS_MODEL_API_KEY` (Bearer) and `JARVIS_MODEL_BASE_URL` at
    construction. Accepts an injectable `httpx` transport (tests pass
    `httpx.MockTransport`); when omitted, real network clients are built
    per call.
    """

    provider_id = "model.adapter"

    def __init__(
        self,
        *,
        model: str = "llama-3.3-70b-versatile",
        timeout_seconds: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        api_key = os.environ.get("JARVIS_MODEL_API_KEY")
        base_url = os.environ.get("JARVIS_MODEL_BASE_URL")
        missing = [
            name
            for name, value in (
                ("JARVIS_MODEL_API_KEY", api_key),
                ("JARVIS_MODEL_BASE_URL", base_url),
            )
            if not value
        ]
        if missing:
            raise ProviderTransportError(
                "adapter configuration incomplete: missing environment variable(s) "
                + ", ".join(missing)
                + " (set at User scope and reopen the terminal)"
            )
        self._api_key: str = api_key  # type: ignore[assignment]
        self._base_url: str = base_url  # type: ignore[assignment]
        self._model = model
        self._timeout = timeout_seconds
        self._transport = transport

    # ---- ProviderAdapter Protocol ----------------------------------------

    async def invoke(
        self, contract_id: str, version: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        schema_json = args.get("schema_json")
        schema_id = args.get("schema_id", "default")
        feedback = args.get("feedback") or []
        if not isinstance(schema_json, dict):
            raise ProviderTransportError(
                f"adapter requires args['schema_json'] (got {type(schema_json).__name__})"
            )
        if contract_id != "model.generate_structured":
            raise ProviderTransportError(
                f"adapter does not support contract {contract_id!r}"
            )

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": self._build_system_prompt(schema_id, schema_json, feedback)},
                {"role": "user", "content": "Emit exactly one JSON object."},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = self._url("/chat/completions").rstrip("/")

        client = self._async_client()
        try:
            async with client:
                return await self._post_json(client, url, payload, headers)
        except ProviderTransportError:
            raise
        except httpx.HTTPError as exc:
            raise ProviderTransportError(f"HTTP transport failure to {url}: {exc}") from exc

    def health_check(self) -> bool:
        url = self._url("/models").rstrip("/")
        client = httpx.Client(timeout=self._timeout, transport=self._transport)
        try:
            with client:
                resp = client.get(url)
            return resp.status_code < 400
        except (httpx.HTTPError, ValueError):
            return False

    # ---- internals --------------------------------------------------------

    def _async_client(self) -> httpx.AsyncClient:
        if self._transport is not None:
            return httpx.AsyncClient(timeout=self._timeout, transport=self._transport)
        return httpx.AsyncClient(timeout=self._timeout)

    async def _post_json(
        self,
        client: httpx.AsyncClient,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise ProviderTransportError(
                f"model provider returned HTTP {resp.status_code}"
            )
        try:
            data = resp.json()
        except ValueError as exc:  # JSONDecodeError → non-JSON 200 body
            raise ProviderTransportError(
                f"model provider returned non-JSON body (HTTP {resp.status_code})"
            ) from exc
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderTransportError(
                "model provider response missing choices[0].message.content"
            ) from exc
        if isinstance(content, str):
            try:
                return json.loads(content)
            except ValueError as exc:
                raise ProviderTransportError(
                    "model returned non-JSON content despite "
                    "response_format=json_object"
                ) from exc
        if isinstance(content, dict):
            return content
        raise ProviderTransportError(
            f"unexpected content type from model: {type(content).__name__}"
        )

    def _url(self, path: str) -> str:
        return f"{self._base_url.rstrip('/')}{path}"

    def _build_system_prompt(
        self, schema_id: str, schema_json: dict[str, Any], feedback: list[str]
    ) -> str:
        prompt = (
            f"You are generating STRICT structured output for schema '{schema_id}'.\n"
            "Reply with a single JSON object conforming exactly to this JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
        )
        if feedback:
            prompt += (
                "\nPrevious outputs failed validation. Fix ALL of the following "
                "problems in your next reply:\n"
                + "\n".join(f"- {item}" for item in feedback)
            )
        return prompt