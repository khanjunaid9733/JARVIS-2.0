from __future__ import annotations

"""M2.4 verification ladder tests (spec §84.4 / docs/M2_4_KICKOFF.md,
ratified items A-F). HERMETIC: no model calls (no provider injected except
where a test deliberately proves the opt-in seam), no new event types, no
ambient state, deterministic — same log + same policy -> identical result
(§84.4 outcome-vs-input precedent, F-M2.3-6 re-applied).

The ladder is DATA: rung_for() is a DATUM lookup on the VerificationPolicy,
never a code branch on memory identity. The cheap rung is ALWAYS available and
hermetic (the frozen M2.3 writer gate); rungs 2-3 are OPT-IN adapter-backed
and escalate ONLY when a provider is injected for an impact class the policy
elevates — otherwise they HOLD. Decisioning is measured by `status`/`rungs`/
`checks`, never by ULID/confidence inputs (§84.4)."""

import pytest

from jarvis.kernel.done_gate import DoneGate
from jarvis.kernel.event_log import EventLog
from jarvis.kernel.memory_api import Memory
from jarvis.kernel.memory_verify import (
    MemoryVerifier,
    VerificationCheck,
    VerificationPolicy,
    VerificationResult,
)
from jarvis.kernel.memory_write import MemoryWriter
from jarvis.kernel.registry import CREATOR_PRINCIPAL_ID

pytestmark = pytest.mark.anyio


class _FixedClock:
    def now_utc_iso(self) -> str:
        return "2026-09-18T00:00:00.000Z"


def _log(tmp_path) -> EventLog:
    return EventLog(db_path=str(tmp_path / "verify.db"), clock=_FixedClock())


def _committed(
    log: EventLog, content: str, source: str, memory_class: str, confidence: float = 1.0
) -> str:
    result = MemoryWriter(log=log).remember(
        content=content,
        source=source,
        confidence=confidence,
        memory_class=memory_class,
    )
    assert result.status == "committed"
    return result.event_ids[-1]


def _event_types(log: EventLog) -> list[str]:
    return [event.event_type for event in log.replay()]


def _rung_names(result: VerificationResult) -> list[tuple[str, str]]:
    """(rung, check-name) across the checks — the WHOLE decisioning datum."""
    return [(c.rung, c.name) for c in result.checks]


def test_cheap_rung_always_available_and_hermetic(tmp_path):
    """Default policy + episodic class -> cheap rung runs, verified, NO provider,
    NO new event types, deterministic (kickoff items A/B; F-C9 hermetic default)."""
    log = _log(tmp_path)
    mem_id = _committed(log, "The blog is built with Astro.", "site.conf", "episodic")
    before = _event_types(log)

    result = MemoryVerifier(log).verify()

    assert result.status == "verified"
    assert result.rungs == ("cheap",)
    assert mem_id in result.mem_ids
    assert "semantic" not in [c.name for c in result.checks]
    assert _event_types(log) == before  # no new event types, no effects

    again = MemoryVerifier(log).verify()
    assert again == result  # determinism: same log + policy -> identical


def test_semantic_rung_holds_without_provider(tmp_path):
    """Semantic impact class escalates by DATUM to the semantic rung; no provider
    -> held (hermetic), never a model call, never an event (kickoff item D/R2)."""
    log = _log(tmp_path)
    mem_id = _committed(log, "Deploy runs on UTC cron.", "ops/runbook.md", "semantic")
    before = _event_types(log)

    result = MemoryVerifier(log).verify()

    assert result.status == "held"
    assert ("semantic", "semantic") in _rung_names(result)
    assert mem_id in result.mem_ids
    semantic = next(c for c in result.checks if c.name == "semantic")
    assert semantic.passed is False
    assert "not configured" in semantic.detail
    assert _event_types(log) == before  # no new event types, hermetic hold


def test_independent_rung_holds_without_provider(tmp_path):
    """Independent escalation (escalated policy ladder DATUM for semantic +
    procedural) + no provider -> held on that rung, hermetic; `independent`
    stays None because no independent rung actually RAN (§84.4 docstring
    contract: 'independent is a dict|None and is None whenever no independent
    rung actually ran')."""
    log = _log(tmp_path)
    mem_id = _committed(log, "Blast door latches.", "hull.manual", "semantic")
    policy = VerificationPolicy(
        ladder={"episodic": "cheap", "semantic": "independent", "procedural": "independent"}
    )

    result = MemoryVerifier(log, policy=policy).verify()

    assert result.status == "held"
    assert ("cheap", "deterministic") in _rung_names(result)
    assert ("independent", "semantic") in _rung_names(result)
    assert mem_id in result.mem_ids
    semantic = next(c for c in result.checks if c.name == "semantic")
    assert semantic.passed is False
    assert "not configured" in semantic.detail
    assert result.independent is None  # never consulted, hermetic


def test_policy_ladder_is_data_not_branches(tmp_path):
    """rung_for() is a DATUM lookup: same code, different policy -> different
    rung for the same memory_class, no dispatch on memory identity (§84.4)."""
    log = _log(tmp_path)
    _committed(log, "Ship weekly.", "guide.md", "procedural")

    default = VerificationPolicy()
    escalated = VerificationPolicy(
        ladder={"episodic": "cheap", "semantic": "independent", "procedural": "independent"}
    )

    assert default.rung_for("procedural") == "semantic"
    assert escalated.rung_for("procedural") == "independent"
    assert escalated.rung_for("episodic") == "cheap"  # never escalated


def test_independent_rung_holds_without_provider_hermetic(tmp_path):
    """Escalated policy with NO provider anywhere -> held, zero effects, zero
    model calls, zero new event types, deterministic (§84.4 / F-C9 / R2)."""
    log = _log(tmp_path)
    _committed(log, "Blast door latches.", "hull.manual", "semantic")
    before = _event_types(log)
    policy = VerificationPolicy(
        ladder={"episodic": "cheap", "semantic": "independent", "procedural": "independent"}
    )

    result = MemoryVerifier(log, policy=policy).verify()

    assert result.status == "held"
    assert result.independent is None
    assert _event_types(log) == before

    again = MemoryVerifier(log, policy=policy).verify()
    assert again == result  # determinism, same log + policy -> identical


class _PassingSemantic:
    """Semantic adapter datum (C-sp1 Protocol: verify(payload) -> (bool, str)):
    hermetic, deterministic, opt-in."""

    def verify(self, payload: dict[str, object]) -> tuple[bool, str]:
        return True, "semantic datum passed"


def _facade(log):
    return Memory(log=log)


def test_memory_facade_verify_seam_is_additive_hermetic_deterministic(tmp_path):
    """Kickoff item F: `Memory.verify` facade seam is ADDITIVE over the same
    hermetic verification datum the writer commits through, defaults to
    cheap/hermetic (no provider injected), never adds event types, is
    deterministic — same log + policy -> identical (facade edge datum)."""
    log = _log(tmp_path)
    _committed(log, "The repository mirrors the frozen writer gate.", "repo.conf", "episodic")
    before = _event_types(log)

    result = _facade(log).verify()

    assert result.status == "verified"
    assert ("cheap", "deterministic") in _rung_names(result)
    assert result.status == "verified"
    assert _event_types(log) == before  # hermetic facade seam: no new event types
    again = _facade(log).verify()
    assert again == result  # determinism through the facade




def test_semantic_rung_runs_when_provider_injected(tmp_path):
    """Item D (opts-in seam): with a SemanticVerifier injected on the datum
    seam, the semantic rung ACTUALLY RUNS and a passing decision is rewarded
    -> verified; fully hermetic + deterministic (	84.4 attached data governed,
    no model call in the frozen path, no new event types, F-C9)."""
    log = _log(tmp_path)
    mem_id = _committed(log, "The blog is built with Astro.", "site.conf", "semantic")
    before = _event_types(log)

    result = MemoryVerifier(log, semantic_verifier=_PassingSemantic()).verify()

    assert result.status == "verified"
    assert ("cheap", "deterministic") in _rung_names(result)
    assert ("semantic", "semantic") in _rung_names(result)
    assert mem_id in result.mem_ids
    semantic = next(c for c in result.checks if c.name == "semantic")
    assert semantic.passed is True
    assert "passed" in semantic.detail
    assert _event_types(log) == before  # no new event types, hermetic

    again = MemoryVerifier(log, semantic_verifier=_PassingSemantic()).verify()
    assert again == result  # determinism: same log + provider datum -> identical
