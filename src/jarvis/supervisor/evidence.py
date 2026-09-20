from __future__ import annotations

"""Evidence hierarchy for the supervisor (M2.5, spec 84.4 evidence precedent).

The rating principle (creator-ratified, M2.4 discovery): the link between a
datum and the current filesystem's ground truth is what the agent can
CONTROL, and confidence must NEVER exceed what the source can support.
Evidence is therefore ordered by how close it sits to the mutable, live,
verified surface of reality:

    filesystem bytes (blobs/exit codes)   -- highest authority
    fresh pytest output                   -- next (only fresh counts)
    git state                             -- dinged by drift
    immutable artifacts                   -- sealed artifacts outrank narration
    tool output                           -- fresh tool datum beats memory
    agent interpretation                  -- may be wrong
    agent memory / claims                 -- lowest

Two hard rules:

1. PERCEIVED-QUALITY DISTINCTION (84.4 precedent): a worker's claim of output
   is provider-mediated narration, NOT a fresh observation of a verifier's
   exit code. Navigation/claims can never outrank fresh verifier bytes.
2. Freshness is the gate: old evidence about a changed filesystem is STALE
   and carries NO authority until re-taken. Any filesystem mutation
   invalidates every prior verification result (stale-result invalidation).

Hermetic default: no ambient I/O in this module; clocks injectable
(FixedClock precedent, M2.4); comparison is deterministic - complex path.
"""


import enum
from dataclasses import dataclass, field
from typing import Protocol


class EvidenceSource(str, enum.Enum):
    """Declared, ordered evidence rungs. Lower ordinal = HIGHER authority."""

    FILESYSTEM = "filesystem"  # 1: read bytes, hash blobs, exit codes
    FRESH_VERIFIER = "fresh_verifier"  # 2: independent verifier output, just run
    GIT_STATE = "git_state"  # 3: diffs/staleness/quotient vs origin
    IMMUTABLE_ARTIFACT = "immutable_artifact"  # 4: sealed/hash-anchored datum
    TOOL_OUTPUT = "tool_output"  # 5: output of an injected tool, fresh run
    AGENT_INTERPRETATION = "agent_interpretation"  # 6: reasoning over evidence
    AGENT_MEMORY = "agent_memory"  # 7: recollection/claims/narration


class EvidencePrecedence(enum.IntEnum):
    """Higher value wins in a conflict (filesystem is 7)."""

    FILESYSTEM = 7
    FRESH_VERIFIER = 6
    GIT_STATE = 5
    IMMUTABLE_ARTIFACT = 4
    TOOL_OUTPUT = 3
    AGENT_INTERPRETATION = 2
    AGENT_MEMORY = 1


_SOURCE_TO_PRECEDENCE = {
    EvidenceSource.FILESYSTEM: EvidencePrecedence.FILESYSTEM,
    EvidenceSource.FRESH_VERIFIER: EvidencePrecedence.FRESH_VERIFIER,
    EvidenceSource.GIT_STATE: EvidencePrecedence.GIT_STATE,
    EvidenceSource.IMMUTABLE_ARTIFACT: EvidencePrecedence.IMMUTABLE_ARTIFACT,
    EvidenceSource.TOOL_OUTPUT: EvidencePrecedence.TOOL_OUTPUT,
    EvidenceSource.AGENT_INTERPRETATION: EvidencePrecedence.AGENT_INTERPRETATION,
    EvidenceSource.AGENT_MEMORY: EvidencePrecedence.AGENT_MEMORY,
}


class Clock(Protocol):
    def now_iso(self) -> str: ...


@dataclass(frozen=True)
class Evidence:
    """A single evidence datum. `precedence` is DECLARED, never derived."""

    source: EvidenceSource
    precedence: EvidencePrecedence
    summary: str
    observed_at: str
    datum: str = ""

    @classmethod
    def declare(cls, source: EvidenceSource, summary: str, observed_at: str) -> "Evidence":
        return cls(
            source=source,
            precedence=_SOURCE_TO_PRECEDENCE[source],
            summary=summary,
            observed_at=observed_at,
        )


@dataclass(frozen=True)
class EvidenceLedger:
    """A full, ordered capture of the live system (filesystem-fresh snapshot).

    Immutable and additive: every observed datum is appended; the ledger never
    drops or reorders past entries (EventLog fold precedent, M2.2). A new
    `observed_at` full capture supersedes but never erases prior rungs.
    """

    observed_at: str
    entries: tuple[Evidence, ...] = field(default_factory=tuple)

    def with_entry(self, entry: Evidence) -> "EvidenceLedger":
        return EvidenceLedger(
            observed_at=entry.observed_at,
            entries=self.entries + (entry,),
        )

    def highest(self) -> Evidence | None:
        """Strongest NON-STALE rung across the live capture."""
        if not self.entries:
            return None
        return max(self.entries, key=lambda e: e.precedence)

    def authority(self) -> Evidence | None:
        """The single most authoritative live datum (filesystem-first)."""
        return self.highest()

    def conflicts(self, claimed: Evidence) -> Evidence | None:
        """If a lower-precedence claim contradicts a higher datum, the higher
        datum is authoritative and is returned as the conflict."""
        authority = self.highest()
        if authority is None or authority.precedence <= claimed.precedence:
            return None
        return authority


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of an independent verification run (fresh, executable exit).

    `value` is enabled ONLY from a source with executable authority
    (filesystem exit code / fresh verifier). Ambient narration can never set
    a true value.
    """

    value: bool
    source: EvidenceSource
    observed_at: str
    evidence: Evidence

    @classmethod
    def decided(
        cls, value: bool, source: EvidenceSource, observed_at: str, summary: str
    ) -> "VerificationResult":
        return cls(
            value=value,
            source=source,
            observed_at=observed_at,
            evidence=Evidence.declare(source, summary, observed_at),
        )
