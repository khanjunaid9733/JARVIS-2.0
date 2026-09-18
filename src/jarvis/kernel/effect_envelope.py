from __future__ import annotations

"""Effect envelope — single-effect PREPARE → AUTHORIZE → COMMIT → VERIFY (module 8).

Per §83 (Complete Effect Pipeline) and §98 (Terminal Verification /
Correction Gate). No effect bypasses the envelope; an effect that reaches
COMMIT but fails VERIFY is NOT complete.

    PREPARE   → build the effect record, emit `effect.prepared`
    AUTHORIZE → fail-closed gate over the manifest and registry:
                the contract is declared in the manifest, its
                requested capabilities ⊆ `manifest.required_capabilities`,
                a provider resolves and a runtime adapter is bound.
                Any failure → `effect.refused`, ZERO adapter invocations.
    COMMIT    → dispatch the bound adapter through the substitution seam
                (ADR-001), emit `effect.committed`.
    VERIFY    → deterministic local check of the adapter result against the
                declared postconditions (§98). Failure → `effect.failed`;
                the effect is NOT complete.

Event stream: stream_id "effect"; types `effect.prepared` /
`effect.authorized` / `effect.committed` / `effect.verified` /
`effect.refused` / `effect.failed`. Exactly one terminal event per run()
(`verified` | `refused` | `failed`). With `log=None` the engine is fully
in-memory: no events table, no disk.

Idempotency: the engine holds `{idempotency_key -> committed envelope}`. A
repeat of a committed key returns the prior envelope marked
`duplicate=True` and emits NO events (checked before PREPARE). The
check → commit → store window is serialized per key, so concurrent runs
with the same key commit exactly once. The map is rebuilt at engine
construction from `effect.verified` events in `log`, so the guarantee
survives an engine restart over the same log (F-A1).

Observability (F-E15, §110.1): the engine accepts an optional `observer`
and wraps each run in a `jarvis.effect.execute` span with the
verification step under `jarvis.verify.postconditions`. Instrumentation is
additive — no observer means NoOp, unchanged behavior.

Causal linkage (F-A2, §112): refused effects are stamped with
`cause_event_id`/`correlation_id` pointing at the run's `effect.prepared`
event, so a replay consumer can attribute a refusal to its intent.

M1 scope (ratified): envelope-only. No real fs/terminal/http adapters;
tests use fake/spy adapters and terminal never performs a real effect.
Multi-effect mission compensation (§83) is deferred.
"""

import asyncio
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .event_log import Clock, Event, EventLog, SystemClock, new_ulid
from .intent import Manifest
from .model_gateway import ProviderResolver
from ..observability import NoOpObserver, effect_span_name, verify_span_name
from .registry import CREATOR_PRINCIPAL_ID, ProviderAdapter


EFFECT_STREAM_ID = "effect"

_EFFECT_EVENT_TYPES = frozenset(
    {
        "effect.prepared",
        "effect.authorized",
        "effect.committed",
        "effect.verified",
        "effect.refused",
        "effect.failed",
    }
)

FailureReason = Literal[
    "refused",
    "unknown_contract",
    "no_provider",
    "adapter_error",
    "unverified",
]

FailurePhase = Literal["prepare", "authorize", "commit", "verify"]


class VerificationResult(BaseModel):
    """Local, deterministic verification outcome (§98). Never model-trusted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool
    detail: str


class EffectEnvelope(BaseModel):
    """The §83 effect record for a single completed effect."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    effect_id: str
    manifest_id: str
    contract_id: str
    contract_version: str
    provider_id: str
    intended_change: dict[str, Any]
    preconditions: dict[str, Any]
    postconditions: dict[str, Any]
    compensation: dict[str, Any] | None
    verification: VerificationResult
    idempotency_key: str
    duplicate: bool = False
    audit_event_ids: list[str]
    committed_at_utc: str


class EffectFailure(BaseModel):
    """Typed refusal/failure. `phase` is where the envelope stopped."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: FailureReason
    detail: str
    phase: FailurePhase


def _verify(
    postconditions: dict[str, Any], result: dict[str, Any]
) -> tuple[bool, str]:
    """Deterministic postcondition check over the adapter's returned dict."""
    if not postconditions:
        return True, "no postconditions declared"
    for key, expected in postconditions.items():
        if key not in result:
            return False, f"postcondition {key!r} missing from adapter result"
        if result[key] != expected:
            return (
                False,
                f"postcondition {key!r}: expected {expected!r}, "
                f"got {result[key]!r}",
            )
    return True, f"{len(postconditions)} postcondition(s) satisfied"


class EffectEnvelopeEngine:
    """Mediates every effect through prepare → authorize → commit → verify.

    `resolver` is the metadata half of the substitution seam (satisfied
    structurally by `CapabilityRegistry`); `adapters` is the runtime half
    and is held privately — there is no public accessor.
    """

    def __init__(
        self,
        resolver: ProviderResolver,
        adapters: dict[str, ProviderAdapter],
        *,
        log: EventLog | None = None,
        clock: Clock | None = None,
        principal_id: str = CREATOR_PRINCIPAL_ID,
        observer: Any | None = None,
    ) -> None:
        self._resolver = resolver
        self._adapters = dict(adapters)
        self._log = log
        self._clock: Clock = clock or SystemClock()
        self._principal_id = principal_id
        self._observer = observer or NoOpObserver()
        self._committed_keys = self._rebuild_committed_keys(log)
        self._locks: dict[str, asyncio.Lock] = {}

    @staticmethod
    def _rebuild_committed_keys(log: EventLog | None) -> dict[str, EffectEnvelope]:
        """Fold committed effects from `effect.verified` events (F-A1).

        `effect.verified` is emitted only when verification passed. The
        in-flight envelope payload there carries the pre-verify fields, so
        replay marks the verification passed and rebuilds the audit chain
        from the effect stream events that share the envelope's effect_id.
        """
        committed: dict[str, EffectEnvelope] = {}
        if log is None:
            return committed
        events = log.replay()
        for event in events:
            if event.event_type != "effect.verified":
                continue
            envelope = EffectEnvelope.model_validate(event.payload)
            audit = [
                e.event_id
                for e in events
                if e.event_type in _EFFECT_EVENT_TYPES
                and e.payload.get("effect_id") == envelope.effect_id
            ]
            committed[envelope.idempotency_key] = envelope.model_copy(
                update={
                    "verification": VerificationResult(
                        passed=True, detail="verified (rebuilt from log)"
                    ),
                    "audit_event_ids": audit,
                }
            )
        return committed

    async def run(
        self,
        manifest: Manifest,
        contract_id: str,
        *,
        intended_change: dict[str, Any],
        preconditions: dict[str, Any] | None = None,
        postconditions: dict[str, Any] | None = None,
        compensation: dict[str, Any] | None = None,
        idempotency_key: str,
        capability_args: dict[str, Any] | None = None,
    ) -> EffectEnvelope | EffectFailure:
        if not idempotency_key:
            raise ValueError("idempotency_key must be non-empty")

        # One span per single-effect run (§110.1: every effect is a child).
        with self._observer.span(
            effect_span_name("execute"), {"contract.id": contract_id}
        ):
            return await self._run_locked(
                manifest,
                contract_id,
                intended_change=intended_change,
                preconditions=preconditions,
                postconditions=postconditions,
                compensation=compensation,
                idempotency_key=idempotency_key,
                capability_args=capability_args,
            )

    async def _run_locked(
        self,
        manifest: Manifest,
        contract_id: str,
        *,
        intended_change: dict[str, Any],
        preconditions: dict[str, Any] | None = None,
        postconditions: dict[str, Any] | None = None,
        compensation: dict[str, Any] | None = None,
        idempotency_key: str,
        capability_args: dict[str, Any] | None = None,
    ) -> EffectEnvelope | EffectFailure:
        # Idempotency is serialized per key: the check → commit → store window
        # contains an await (adapter.invoke), so without a lock two concurrent
        # runs with the same key could both commit. See effect-idempotency fix.
        lock = self._locks.get(idempotency_key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[idempotency_key] = lock
        async with lock:
            prior = self._committed_keys.get(idempotency_key)
            if prior is not None:
                return prior.model_copy(update={"duplicate": True})
            return await self._execute(
                manifest,
                contract_id,
                intended_change=intended_change,
                preconditions=preconditions,
                postconditions=postconditions,
                compensation=compensation,
                idempotency_key=idempotency_key,
                capability_args=capability_args,
            )

    async def _execute(
        self,
        manifest: Manifest,
        contract_id: str,
        *,
        intended_change: dict[str, Any],
        preconditions: dict[str, Any] | None = None,
        postconditions: dict[str, Any] | None = None,
        compensation: dict[str, Any] | None = None,
        idempotency_key: str,
        capability_args: dict[str, Any] | None = None,
    ) -> EffectEnvelope | EffectFailure:
        envelope = EffectEnvelope(
            effect_id=new_ulid(),
            manifest_id=manifest.manifest_id,
            contract_id=contract_id,
            contract_version="",
            provider_id="",
            intended_change=dict(intended_change),
            preconditions=dict(preconditions or {}),
            postconditions=dict(postconditions or {}),
            compensation=compensation,
            verification=VerificationResult(passed=False, detail="not yet verified"),
            idempotency_key=idempotency_key,
            duplicate=False,
            audit_event_ids=[],
            committed_at_utc=self._clock.now_utc_iso(),
        )

        # ---- PREPARE ----
        audit: list[str] = []
        self._emit_into(audit, "effect.prepared", envelope)

        # ---- AUTHORIZE (fail-closed; no adapter call on refusal) ----
        contract_ref = next(
            (c for c in manifest.contracts if c.id == contract_id), None
        )
        if contract_ref is None:
            return self._refuse(
                envelope,
                "unknown_contract",
                f"contract {contract_id!r} is not declared in manifest "
                f"{manifest.manifest_id!r}",
                audit,
            )

        requested = set(intended_change.get("requested_capabilities") or [])
        granted = set(manifest.required_capabilities)
        if not requested.issubset(granted):
            return self._refuse(
                envelope,
                "refused",
                f"requested capabilities {sorted(requested - granted)} are "
                "outside the manifest's granted set",
                audit,
            )

        constraint = contract_ref.version
        provider_id = self._resolver.resolve_provider(contract_id, constraint)
        if provider_id is None:
            return self._refuse(
                envelope,
                "no_provider",
                f"no registered provider for {contract_id}@{constraint}",
                audit,
            )
        contract_version = self._resolver.resolve_version(contract_id, constraint)
        if contract_version is None:
            return self._refuse(
                envelope,
                "no_provider",
                f"provider {provider_id!r} resolved no version for "
                f"{contract_id}@{constraint}",
                audit,
            )
        adapter = self._adapters.get(provider_id)
        if adapter is None:
            return self._refuse(
                envelope,
                "no_provider",
                f"no runtime adapter bound for provider {provider_id!r}",
                audit,
            )

        envelope = envelope.model_copy(
            update={
                "contract_version": contract_version,
                "provider_id": provider_id,
            }
        )
        self._emit_into(audit, "effect.authorized", envelope)

        # ---- COMMIT ----
        args = (
            dict(capability_args)
            if capability_args is not None
            else dict(contract_ref.args)
        )
        try:
            result = await adapter.invoke(contract_id, contract_version, args)
        except Exception as exc:  # adapter contract violation
            self._emit_into(audit, "effect.failed", envelope)
            return EffectFailure(
                reason="adapter_error",
                detail=f"{type(exc).__name__}: {exc}",
                phase="commit",
            )
        if not isinstance(result, dict):
            self._emit_into(audit, "effect.failed", envelope)
            return EffectFailure(
                reason="adapter_error",
                detail=f"adapter returned {type(result).__name__}, expected dict",
                phase="commit",
            )
        self._emit_into(audit, "effect.committed", envelope)

        # ---- VERIFY (§98) ----
        with self._observer.span(
            verify_span_name("postconditions"), {"contract.id": contract_id}
        ):
            passed, detail = _verify(envelope.postconditions, result)
        verification = VerificationResult(passed=passed, detail=detail)
        if not passed:
            failed = envelope.model_copy(update={"verification": verification})
            self._emit_into(audit, "effect.failed", failed)
            return EffectFailure(reason="unverified", detail=detail, phase="verify")

        self._emit_into(audit, "effect.verified", envelope)
        completed = envelope.model_copy(
            update={"verification": verification, "audit_event_ids": audit}
        )
        self._committed_keys[idempotency_key] = completed
        return completed

    # ---- internals --------------------------------------------------------

    def _refuse(
        self,
        envelope: EffectEnvelope,
        reason: FailureReason,
        detail: str,
        audit: list[str],
    ) -> EffectFailure:
        # F-A2: attribute the refusal to its intent via the prepared event id.
        cause = audit[0] if audit else None
        self._emit_into(
            [],
            "effect.refused",
            envelope,
            cause_event_id=cause,
            correlation_id=cause,
        )
        return EffectFailure(reason=reason, detail=detail, phase="authorize")

    def _emit_into(
        self,
        audit: list[str],
        event_type: str,
        envelope: EffectEnvelope,
        *,
        cause_event_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        event_id = self._emit(
            event_type,
            envelope,
            cause_event_id=cause_event_id,
            correlation_id=correlation_id,
        )
        if event_id is not None:
            audit.append(event_id)

    def _emit(
        self,
        event_type: str,
        envelope: EffectEnvelope,
        *,
        cause_event_id: str | None = None,
        correlation_id: str | None = None,
    ) -> str | None:
        if self._log is None:
            return None
        event = Event(
            stream_id=EFFECT_STREAM_ID,
            event_type=event_type,
            principal_id=self._principal_id,
            cause_event_id=cause_event_id,
            correlation_id=correlation_id,
            payload=envelope.model_dump(),
        )
        return self._log.append(event)
