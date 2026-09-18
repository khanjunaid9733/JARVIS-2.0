from __future__ import annotations

"""Freebuff/DeepSeek red-team evidence tests — modules 4 & 6 review.

IMPORTANT: these tests DOCUMENT current behavior that the review flags as
defective. They assert what the code does TODAY, with comments explaining
what it SHOULD do. They are review evidence, not acceptance criteria. If a
fix lands, the assertion should be flipped to the "SHOULD" form.

Attack surfaces covered (see review report for full findings):
- F2: adapter leaks raw json.JSONDecodeError on non-JSON 200/3xx bodies ->
      gateway mislabels provider-body faults as `adapter_error`.
- F3: fallback execution records the PRIMARY binding's contract_version.
- F4: re-registering a provider never changes first-registered precedence.
- F5: caret dialect mis-resolves ^0.x and matches pre-release versions.
- F6: schema_id is not bound to the schema it labels.
"""

import json

import httpx
import pytest
from pydantic import BaseModel

from jarvis.kernel.model_gateway import (
    ModelGateway,
    RoleContract,
    ValidatedOutput,
)
from jarvis.kernel.registry import (
    CapabilityRegistry,
    ContractDef,
    ProviderBinding,
    ProviderMeta,
)
from jarvis.providers.openai_compatible import OpenAICompatibleAdapter

pytestmark = pytest.mark.anyio

# Deliberately fake sentinel — the review found a real-format key committed
# in tests/providers/test_openai_compatible.py:17 (finding F1). Do not copy it.
FAKE_KEY = "gsk_REDACTED_REVIEW_SENTINEL_0000"


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("JARVIS_MODEL_API_KEY", FAKE_KEY)
    monkeypatch.setenv("JARVIS_MODEL_BASE_URL", "https://api.example.com/v1")


class Note(BaseModel):
    text: str
    n: int = 0


class Other(BaseModel):
    q: str


def _meta(provider_id: str, fallback: str | None = None) -> ProviderMeta:
    return ProviderMeta(
        provider_id=provider_id,
        version="1.0.0",
        license="MIT",
        license_compatibility="approved",
        adapter="jarvis.providers.test",
        trust_level="trusted",
        process_model="in_process",
        network="none",
        health_check="probe",
        cve_status="checked_clean",
        provenance_added_by="creator",
        provenance_added_at_utc="2026-09-16T00:00:00Z",
        provenance_reason="red-team review fixture",
        fallback_provider_id=fallback,
    )


def _contract(contract_id: str, version: str) -> ContractDef:
    return ContractDef(
        contract_id=contract_id,
        version=version,
        args_schema={"x": {"type": "string", "required": True}},
    )


def _binding(provider_id: str, contracts: list[ContractDef], fallback=None):
    return ProviderBinding(meta=_meta(provider_id, fallback), contracts=contracts)


# ---------------------------------------------------------------------------
# F2: non-JSON 200 body -> raw exception leaks; gateway labels adapter_error
# ---------------------------------------------------------------------------


async def test_evidence_empty_200_body_leaks_raw_json_decode_error(env):
    """SHOULD raise ProviderTransportError; TODAY raises raw JSONDecodeError.

    httpx.Response.json() on an empty body raises json.JSONDecodeError, which
    is a ValueError, not httpx.HTTPError — so the adapter's except clause
    (openai_compatible.py:111) does not convert it.
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b""))
    adapter = OpenAICompatibleAdapter(transport=transport)

    with pytest.raises(json.JSONDecodeError):  # NOT ProviderTransportError
        await adapter.invoke(
            "model.generate_structured",
            "1.0.0",
            {"schema_id": "note", "schema_json": {"type": "object"}},
        )


async def test_evidence_redirect_302_body_mislabels_as_adapter_error(env):
    """SHOULD map to transport_error; TODAY the gateway says adapter_error.

    httpx defaults to follow_redirects=False, so a 302 comes back as-is,
    falls under the `status_code >= 400` bar, and the empty body triggers
    the same raw JSONDecodeError — which the gateway's broad
    `except Exception` (model_gateway.py:240) labels "adapter contract
    violation" even though the provider/transport is at fault.
    """
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            302, headers={"location": "https://elsewhere.example/v1"}, content=b""
        )
    )
    adapter = OpenAICompatibleAdapter(transport=transport)
    registry = CapabilityRegistry.seed_m1_defaults()
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": adapter})

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert result.reason == "adapter_error"  # evidence: mislabeled; expected transport_error


# ---------------------------------------------------------------------------
# F3: fallback runs, but ValidatedOutput records the PRIMARY contract_version
# ---------------------------------------------------------------------------


async def test_evidence_fallback_records_primary_contract_version():
    """SHOULD record the active (fallback) provider's contract version; TODAY
    contract_version is resolved from the primary binding (model_gateway.py:201)
    while provider_id is the fallback — a provenance mismatch under ADR-004."""
    registry = CapabilityRegistry()
    registry.register_provider("creator", _binding(
        "model.primary",
        [_contract("model.generate_structured", "1.0.0")],
        fallback="model.backup",
    ))
    registry.register_provider(
        "creator", _binding("model.backup", [_contract("model.generate_structured", "1.2.0")])
    )

    class BackupAdapter:
        provider_id = "model.backup"

        async def invoke(self, contract_id, version, args):
            # The adapter is invoked with the PRIMARY version string:
            assert version == "1.0.0", f"invoked with {version}, not backup's 1.2.0"
            return {"text": "from-backup"}

        def health_check(self):
            return True

    gateway = ModelGateway(resolver=registry, adapters={"model.backup": BackupAdapter()})
    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert isinstance(result, ValidatedOutput)
    assert result.provider_id == "model.backup"          # adapter that ran
    assert result.contract_version == "1.0.0"            # primary's version — mismatch


# ---------------------------------------------------------------------------
# F4: re-registration never changes first-registered precedence
# ---------------------------------------------------------------------------


def test_evidence_reregistered_provider_keeps_old_precedence():
    """Documented M1 rule, but note the creator-intent trap: re-registering
    provider B (latest creator action) does NOT let it win resolution."""
    registry = CapabilityRegistry()
    registry.register_provider("creator", _binding("prov.a", [_contract("c.x", "1.0.0")]))
    registry.register_provider("creator", _binding("prov.b", [_contract("c.x", "1.0.0")]))

    assert registry.resolve_provider("c.x", "1.0.0") == "prov.a"

    # Creator re-registers B with a *different* schema — still loses:
    registry.register_provider(
        "creator",
        _binding("prov.b", [ContractDef(
            contract_id="c.x", version="1.0.0",
            args_schema={"y": {"type": "integer", "required": True}},
        )]),
    )
    assert registry.resolve_provider("c.x", "1.0.0") == "prov.a"
    assert registry.get_args_schema("c.x", "1.0.0") == {"x": {"type": "string", "required": True}}


# ---------------------------------------------------------------------------
# F5: caret dialect — ^0.x and pre-release mis-resolution
# ---------------------------------------------------------------------------


def test_evidence_caret_zero_dot_x_matches_any_minor():
    """^0.2 SHOULD mean >=0.2.0,<0.3.0 (or be rejected); TODAY it matches any
    0.y.z whose major is 0 — e.g. 0.9.0 'resolves' under ^0.2."""
    registry = CapabilityRegistry()
    registry.register_provider("creator", _binding("prov.c", [_contract("c.y", "0.9.0")]))

    assert registry.has_contract("c.y", "^0.2") is True      # evidence of defect
    assert registry.resolve_version("c.y", "^0.2") == "0.9.0"


def test_evidence_prerelease_matches_caret_major():
    """Pre-release '1.1.0-beta' SHOULD not satisfy a stable ^1 constraint
    without explicit policy; TODAY the string prefix matches."""
    registry = CapabilityRegistry()
    registry.register_provider("creator", _binding("prov.d", [_contract("c.z", "1.1.0-beta")]))

    assert registry.has_contract("c.z", "^1") is True        # evidence of defect


# ---------------------------------------------------------------------------
# F6: schema_id is not bound to the schema it labels
# ---------------------------------------------------------------------------


async def test_evidence_same_schema_id_two_different_schemas(env):
    """schema_id is a free-text label (model_gateway.py:220); two callers may
    reuse one schema_id for different schemas with no error and no binding —
    audit ambiguity: schema_id alone cannot identify the schema later."""
    class CapturingAdapter:
        provider_id = "model.adapter"

        def __init__(self):
            self.seen = []

        async def invoke(self, contract_id, version, args):
            self.seen.append((args["schema_id"], args["schema_json"]))
            return {"text": "ok"} if args["schema_id"] == "thing" and "text" in args["schema_json"]["properties"] else {"q": "ok"}

        def health_check(self):
            return True

    cap = CapturingAdapter()
    registry = CapabilityRegistry.seed_m1_defaults()
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": cap})

    out1 = await gateway.generate_structured(
        RoleContract.SCHEMA_CONSTRAINED, Note, schema_id="thing"
    )
    out2 = await gateway.generate_structured(
        RoleContract.SCHEMA_CONSTRAINED, Other, schema_id="thing"
    )

    assert isinstance(out1, ValidatedOutput) and isinstance(out2, ValidatedOutput)
    assert cap.seen[0][0] == cap.seen[1][0] == "thing"       # same label…
    assert cap.seen[0][1] != cap.seen[1][1]                  # …different schemas
