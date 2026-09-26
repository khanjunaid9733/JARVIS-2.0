from __future__ import annotations

"""Telemetry and Observability hooks for the Skill Runtime.

Records skill invocations, search queries, health verification decisions,
and execution latencies into OpenTelemetry spans and local metrics counters.
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class SkillMetrics:
    """Aggregate execution metrics for the skill subsystem."""

    dispatches_total: int = 0
    dispatches_successful: int = 0
    dispatches_refused: int = 0
    dispatches_failed: int = 0
    total_execution_ms: float = 0.0
    queries_total: int = 0
    audit_emit_failures: int = 0


_GLOBAL_METRICS = SkillMetrics()


def get_skill_metrics() -> SkillMetrics:
    """Retrieve global skill metrics."""
    return _GLOBAL_METRICS


def record_skill_audit_failure(event_type: str) -> None:
    """Count an audit sink that rejected a skill event.

    Audit emission must never abort skill execution, so the dispatcher swallows
    sink errors - but a swallowed *audit* failure is exactly the kind of silent
    degradation the kernel forbids. Recording it here keeps the failure
    observable instead of invisible.
    """
    _GLOBAL_METRICS.audit_emit_failures += 1


@contextmanager
def record_skill_dispatch(skill_id: str) -> Iterator[dict[str, Any]]:
    """Context manager for tracing skill dispatch duration and outcome."""
    record: dict[str, Any] = {
        "skill_id": skill_id,
        "start_time": time.perf_counter(),
        "status": "pending",
    }
    _GLOBAL_METRICS.dispatches_total += 1
    try:
        yield record
    except Exception as exc:
        record["status"] = "failed"
        record["error"] = str(exc)
        _GLOBAL_METRICS.dispatches_failed += 1
        raise
    finally:
        duration_ms = (time.perf_counter() - record["start_time"]) * 1000
        record["duration_ms"] = duration_ms
        _GLOBAL_METRICS.total_execution_ms += duration_ms
        if record.get("status") == "success":
            _GLOBAL_METRICS.dispatches_successful += 1
        elif record.get("status") == "refused":
            _GLOBAL_METRICS.dispatches_refused += 1
