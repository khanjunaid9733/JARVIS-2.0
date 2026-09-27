from __future__ import annotations

"""Capability resolution - the ONE place a step's declared need meets the fabric.

A mission step declares the datum its own work must produce (`step_capability` in
`jarvis.live_steps`). This module resolves that declaration against the capability
fabric (spec §20) and says exactly what happened:

* it ranks the library with the EXISTING engine (`SkillRuntimeEngine` - no second
  dispatcher, no parallel registry) for the declared query,
* it tries the ranked candidates IN ORDER through the existing `SkillDispatcher`
  until one produces a well-formed datum (a sha256 hex digest), because the
  ranking is fuzzy over declared identities and a capable-looking neighbour really
  does outrank the right skill (measured on this library: the text-digest skill
  scored 129.09 on the FILE digest query against files-hash's 120.70),
* it labels the outcome `real - skill <id> ...` (a skill in the fabric produced
  the datum, audits on the mission's stream) or `seam - <reason>` (no candidate
  could, every reason named, and the deterministic local path produced it
  instead).

Correctness is NOT decided here. `CapabilityResolver` decides capability only -
which candidate can produce a datum - while the fresh-process independent
verifier (`jarvis.live_dispatch`) recomputes that datum from the subject bytes, so
a skill that lies fails the step.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from .kernel.event_log import EventLog
from .live_steps import ARTIFACT_DIRNAME, WORK_ORDER_DIRNAME, step_capability

if TYPE_CHECKING:  # typing only: the fabric is imported on first USE, below
    from .skills.engine import SkillRuntimeEngine

#: How many ranked candidates one declared need may try before the loop gives up
#: and says so. Rank 1 is not trusted on its own: the ranking is fuzzy over
#: declared identities and it really does mis-rank (see the module docstring),
#: so a candidate only counts once it produces a well-formed datum.
CAPABILITY_CANDIDATE_LIMIT = 3
CAPABILITY_AUDIT_STREAM = "skills"
SKILL_TIMEOUT_SECONDS = 30.0

#: A content-address is exactly one sha256 hex digest; anything else is not one.
_SHA256_TOKEN = re.compile(r"\b[0-9a-fA-F]{64}\b")


def first_sha256_token(text: str) -> str | None:
    """The first sha256 hex digest in `text`, or None when there is none."""
    match = _SHA256_TOKEN.search(text or "")
    return match.group(0).lower() if match else None


@dataclass(frozen=True)
class CapabilityDatum:
    """What one step's declared capability need resolved to.

    A datum, never a claim: `label` says exactly how it was produced (`real - `
    when a skill in the fabric produced it, `seam - ` when every candidate was
    tried and none could, each reason named) and `field` names the artifact field
    it goes into. `skill_id` is empty for a seam.
    """

    step_id: str
    attempt: int
    field: str
    datum: str
    label: str
    skill_id: str | None = None


class CapabilityResolver:
    """Resolves each step's declared need through the fabric, labeling the truth.

    Built by `jarvis.live_boot.boot_runtime` with the mission's own log as the
    audit sink, so every skill dispatch lands in the real hash chain. Every datum
    it resolves is kept in `datums` (per attempt) so the report can state what
    really happened instead of an assumed provenance.
    """

    def __init__(
        self,
        *,
        workspace: Path,
        sandbox: Any,
        log: EventLog | None = None,
        engine: SkillRuntimeEngine | None = None,
        base_dir: str = ARTIFACT_DIRNAME,
        order_dir: str = WORK_ORDER_DIRNAME,
    ) -> None:
        self._workspace = workspace
        self._sandbox = sandbox
        self._log = log
        self._engine_instance = engine
        self._base_dir = base_dir
        self._order_dir = order_dir
        self.datums: list[CapabilityDatum] = []

    @property
    def workspace(self) -> Path:
        return self._workspace

    def engine(self) -> SkillRuntimeEngine:
        """The skill runtime, built on first use with THIS mission's log as its
        audit sink, so every skill dispatch lands in the real hash chain.

        Imported here, not at module load: the fabric is a separate subsystem and
        a voice turn (or a checkout where it cannot import) must not be dragged
        down with it. `resolve` treats any failure as a seam.
        """
        if self._engine_instance is None:
            from .skills.engine import SkillRuntimeEngine

            self._engine_instance = SkillRuntimeEngine(event_sink=self._log)
        return self._engine_instance

    def built_engine(self) -> SkillRuntimeEngine | None:
        """The engine if it has been built, else None - for honest reporting."""
        return self._engine_instance

    def indexed_skills(self) -> str:
        """How much fabric this run really holds, for the component listing."""
        engine = self._engine_instance
        return "registry n/a" if engine is None else f"{engine.registry.count()} skills indexed"

    def _subject_digest(self, declaration: Mapping[str, Any]) -> str:
        """The deterministic content-address of a declared subject's bytes.

        This is the SEAM value: it is what the step's datum is when the fabric
        cannot produce one. It is never used to check a skill's answer - the
        independent verifier does that, and it recomputes from the same bytes.
        """
        if declaration.get("shape") == "text":
            return hashlib.sha256(str(declaration.get("value", "")).encode("utf-8")).hexdigest()
        try:
            return str(self._sandbox.read_file(str(declaration.get("value", "")))["sha256"])
        except Exception:
            return ""

    def resolve(self, step_id: str, *, mission_id: str, goal: str, attempt: int) -> CapabilityDatum:
        """Resolve ONE step's declared capability need through the fabric.

        The need comes from the step's OWN contract (`step_capability`): the datum
        its work must produce. Nothing here names a skill. Skipping an INCAPABLE
        candidate is the loop's whole judgement; the CORRECTNESS of a produced
        datum is never decided here - the fresh-process verifier recomputes it
        from the subject bytes, so a skill that lies fails the step.

        The label always starts with `real -` (a skill in the fabric produced this
        step's datum) or `seam -` (no candidate could, with every reason named),
        so a fallback can never be reported as a capability.
        """
        declaration = step_capability(
            step_id,
            mission_id=mission_id,
            goal=goal,
            base_dir=self._base_dir,
            order_dir=self._order_dir,
        )
        if not declaration:
            return self._record(CapabilityDatum(step_id, attempt, "", "", "", None))
        field = str(declaration["field"])
        local = self._subject_digest(declaration)
        subject = str(declaration["subject"])
        argument = (
            str(declaration["value"])
            if declaration["shape"] == "text"
            else str(self._workspace / str(declaration["value"]))
        )
        tried: list[str] = []
        try:
            from .skills.context import SkillExecutionContext

            engine = self.engine()
            _top, candidates = engine.resolve_skill(str(declaration["query"]))
        except Exception as exc:  # a broken fabric is a seam, never a crash
            return self._record(
                CapabilityDatum(
                    step_id,
                    attempt,
                    field,
                    local,
                    f"seam - the skill fabric raised {type(exc).__name__}: {exc}; {field!r} "
                    "was computed by the deterministic local path",
                    None,
                )
            )
        if not candidates:
            return self._record(
                CapabilityDatum(
                    step_id,
                    attempt,
                    field,
                    local,
                    f"seam - the registry holds {engine.registry.count()} skills and ranked no "
                    f"candidate for {declaration['query']!r}; {field!r} was computed by the "
                    "deterministic local path",
                    None,
                )
            )
        context = SkillExecutionContext(
            workspace=self._workspace,
            parameters={str(declaration["parameter"]): argument},
            timeout_seconds=SKILL_TIMEOUT_SECONDS,
            mission_id=mission_id,
        )
        limit = min(len(candidates), CAPABILITY_CANDIDATE_LIMIT)
        for rank, match in enumerate(candidates[:limit], start=1):
            result = engine.dispatcher.dispatch(match.skill, context)
            if result.is_refused:
                tried.append(f"{match.skill.id!r}: refused ({result.refusal_reason})")
                continue
            if not result.success:
                tried.append(f"{match.skill.id!r}: {result.error or 'failed'}")
                continue
            digest = first_sha256_token(result.raw_output)
            if digest is None:
                tried.append(f"{match.skill.id!r}: exit 0 but emitted no sha256 digest")
                continue
            return self._record(
                CapabilityDatum(
                    step_id,
                    attempt,
                    field,
                    digest,
                    f"real - skill {match.skill.id!r} produced {field!r} for {subject} "
                    f"(registry candidate {rank} of {limit} for {declaration['query']!r}, "
                    f"exit 0 in {result.duration_ms:.0f}ms, audits on stream "
                    f"{CAPABILITY_AUDIT_STREAM!r})"
                    + (f"; skipped first: {'; '.join(tried)}" if tried else "")
                    + "; the fresh-process verifier recomputes this datum from the subject, "
                    "so the skill's answer is adjudicated, not trusted",
                    match.skill.id,
                )
            )
        return self._record(
            CapabilityDatum(
                step_id,
                attempt,
                field,
                local,
                f"seam - {limit} candidate(s) were tried for {declaration['query']!r} and none "
                f"produced {field!r} for {subject} ({'; '.join(tried)}); {field!r} was computed "
                "by the deterministic local path",
                None,
            )
        )

    def _record(self, datum: CapabilityDatum) -> CapabilityDatum:
        self.datums.append(datum)
        return datum


__all__ = [
    "CAPABILITY_AUDIT_STREAM",
    "CAPABILITY_CANDIDATE_LIMIT",
    "SKILL_TIMEOUT_SECONDS",
    "CapabilityDatum",
    "CapabilityResolver",
    "first_sha256_token",
]
