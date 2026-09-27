from __future__ import annotations

"""The mission step model - the ONE place a step's contract is declared.

A live mission is a fixed, ordered pipeline of three steps, and every step's
claim about its own work lives here, together, so a maintainer reading one file
knows exactly what each step declares:

* which steps exist and in which order (`LocalDecomposer`),
* where their artifacts live (`WORK_ORDER_DIRNAME`, `ARTIFACT_DIRNAME`),
* the artifact each step produces (`step_payload`) and the datum it must carry,
* what the independent verifier must find for it (`step_expectations`),
* the capability its work needs, declared as a QUERY rather than a skill id
  (`step_capability` + `CAPABILITY_QUERIES`) - which skill answers it is the
  registry's ranking to decide, never this module's.

`step_payload`'s datum must be the datum `step_expectations` makes the verifier
recompute (the mission intent's content-address on `plan`/`deliver`, the
deliverable's on `attest`) - that agreement is why the declarations sit beside
each other here instead of in the dispatch seam or the composition root.

The worker, the independent verifier and their containment live in
`jarvis.live_dispatch`; the bootstrap and the capability resolution live in
`jarvis.live_boot` / `jarvis.live_capability`. This module imports none of them:
the step model is pure data about steps.
"""

import json
from typing import Any, Mapping, Sequence

from .orchestrator.mission_runner import MissionStep

#: The declared pipeline: plan -> deliver -> attest. The runner folds it; it
#: never folds itself.
PLAN_STEP = "plan"
DELIVER_STEP = "deliver"
ATTEST_STEP = "attest"

WORK_ORDER_DIRNAME = "work_orders"
ARTIFACT_DIRNAME = "artifacts"


def goal_digest(goal: str) -> str:
    import hashlib

    return hashlib.sha256(goal.encode("utf-8")).hexdigest()


def step_payload(
    step: MissionStepLike,  # noqa: F821 - see alias below
    *,
    mission_id: str,
    goal: str,
    step_ids: Sequence[str],
    attempt: int,
    carried: str,
    goal_sha256: str | None = None,
    deliverable_sha256: str | None = None,
    digest_source: str = "",
    base_dir: str = ARTIFACT_DIRNAME,
    order_dir: str = WORK_ORDER_DIRNAME,
) -> tuple[str, str]:
    """The step's declared artifact path and exact bytes.

    Every body records WHO produced its content-address (`digest_source`), so an
    artifact can never claim a digest without declaring where it came from - a
    skill the fabric resolved, or the deterministic local path. `goal_sha256` and
    `deliverable_sha256` carry the datum the step's declared capability produced;
    `None` means the producer did not supply one and the declared bytes are
    addressed locally instead.
    """
    goal_address = goal_digest(goal) if goal_sha256 is None else goal_sha256
    if step.id == PLAN_STEP:
        relative = f"{order_dir}/{mission_id}.json"
        body: dict[str, Any] = {
            "mission_id": mission_id,
            "goal": goal,
            "goal_sha256": goal_address,
            "attempt": attempt,
            "steps": list(step_ids),
            "digest_source": digest_source,
        }
    elif step.id == ATTEST_STEP:
        deliverable = f"{base_dir}/{mission_id}.json"
        relative = f"{deliverable}.sha256"
        body = {
            "deliverable": deliverable,
            "sha256": deliverable_sha256 or "",
            "mission_id": mission_id,
            "attempt": attempt,
            "digest_source": digest_source,
        }
    else:
        relative = f"{base_dir}/{mission_id}.json"
        body = {
            "mission_id": mission_id,
            "step": step.id,
            "goal": goal,
            "goal_sha256": goal_address,
            "attempt": attempt,
            "recovered": attempt > 1,
            "recovery_context": carried,
            "digest_source": digest_source,
        }
    return relative, json.dumps(body, sort_keys=True, indent=2) + "\n"


def step_expectations(
    step_id: str,
    *,
    mission_id: str,
    goal: str,
    step_ids: Sequence[str],
    deliverable: str,
    base_dir: str = ARTIFACT_DIRNAME,
    order_dir: str = WORK_ORDER_DIRNAME,
) -> dict[str, Any]:
    """What the independent verifier must find for this step, as pure data."""
    if step_id == PLAN_STEP:
        return {
            "kind": PLAN_STEP,
            "mission_id": mission_id,
            "goal": goal,
            "steps": len(step_ids),
            "path": f"{order_dir}/{mission_id}.json",
        }
    if step_id == ATTEST_STEP:
        return {
            "kind": ATTEST_STEP,
            "mission_id": mission_id,
            "deliverable": deliverable,
            "path": f"{deliverable}.sha256",
        }
    return {
        "kind": DELIVER_STEP,
        "mission_id": mission_id,
        "goal": goal,
        "goal_sha256": goal_digest(goal),
        "path": f"{base_dir}/{mission_id}.json",
    }


#: The capability queries a step may declare. A step names the SHAPE of the
#: subject bytes its work must content-address; which skill answers that is the
#: registry's ranking to decide, never this module's.
CAPABILITY_QUERIES: Mapping[str, str] = {
    "text": "compute the sha256 checksum hash digest of a text string",
    "file": "compute the sha256 checksum hash digest of a file",
}


def step_capability(
    step_id: str,
    *,
    mission_id: str,
    goal: str,
    base_dir: str = ARTIFACT_DIRNAME,
    order_dir: str = WORK_ORDER_DIRNAME,
) -> dict[str, Any]:
    """The capability a step's OWN declared work needs, or {} when it needs none.

    Declared beside `step_payload` and `step_expectations` because the datum the
    fabric must produce is exactly the datum the independent verifier recomputes:
    the mission intent's content-address on the `plan` and `deliver` steps
    (`goal_sha256`, recomputed from the goal bytes) and the deliverable's on
    `attest` (`sha256`, recomputed from the file on disk). A step whose work needs
    nothing from the fabric declares nothing and is left alone.
    """
    if step_id in (PLAN_STEP, DELIVER_STEP):
        return {
            "field": "goal_sha256",
            "subject": "the mission goal text",
            "shape": "text",
            "value": goal,
            "query": CAPABILITY_QUERIES["text"],
            "parameter": "text",
        }
    if step_id == ATTEST_STEP:
        return {
            "field": "sha256",
            "subject": f"the deliverable {base_dir}/{mission_id}.json",
            "shape": "file",
            "value": f"{base_dir}/{mission_id}.json",
            "query": CAPABILITY_QUERIES["file"],
            "parameter": "path",
        }
    return {}


# `step_payload`/`step_expectations` take a `MissionStep`-shaped object; kept as
# a string annotation above to avoid importing the orchestrator at module load.
MissionStepLike = Any


class LocalDecomposer:
    """The declared decomposition seam (M3.2 `Decomposer`): deterministic and
    local. The plan is ordered; the runner folds it, it never folds itself."""

    def decompose(self, goal: str) -> tuple[MissionStep, ...]:
        return (
            MissionStep(id="plan", summary=f"write the mission work order for {goal!r}"),
            MissionStep(id="deliver", summary="write the mission deliverable artifact"),
            MissionStep(id="attest", summary="content-address the deliverable on disk"),
        )


__all__ = [
    "ARTIFACT_DIRNAME",
    "ATTEST_STEP",
    "CAPABILITY_QUERIES",
    "DELIVER_STEP",
    "LocalDecomposer",
    "MissionStepLike",
    "PLAN_STEP",
    "WORK_ORDER_DIRNAME",
    "goal_digest",
    "step_capability",
    "step_expectations",
    "step_payload",
]
