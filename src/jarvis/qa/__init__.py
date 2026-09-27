"""Quality-assurance tooling for JARVIS.

`bugscan` finds real defect classes deterministically. `triage` adds AI
explanation and patch proposals on top, gated behind a human.
"""

from __future__ import annotations

from .bugscan import Finding, ScanReport, scan
from .triage import ApplyResult, Triage, propose_apply, triage_one

__all__ = [
    "Finding",
    "ScanReport",
    "scan",
    "Triage",
    "triage_one",
    "ApplyResult",
    "propose_apply",
]
