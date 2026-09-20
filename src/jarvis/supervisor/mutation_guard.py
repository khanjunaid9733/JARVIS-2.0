from __future__ import annotations

"""Mutation guard - the post-PASS file mutation detector (M2.5, spec 84.4).

This is the machine that would have CRUSHED the M2.4 drift failure as a
non-event: once a package reaches PASS and is sealed, ANY post-PASS edit to
the sealed blob set is a MUTATION. The mutation guard re-measures the actual
filesystem blobs (highest evidence rung - filesystem precedence, spec 84.4 /
evidence.py) against a FROZEN snapshot taken at PASS. It never asks the
worker "did you change anything?" - it reads bytes and compares hashes. A
worker narration can never veto the byte datum.

Determinism: same sealed snapshot + same current blobs -> identical report.
Clocks are injected (never ambient); the snapshot is compared by hash, never
by narration or mtime (mtime is ambient clock narration - it is a freshness
HINT at most, never a decision input, 84.4 precedent).

The mutation guard is INDEPENDENT of the worker: it is not handed the
worker's claims, it is handed the filesystem. Same log + same policy ->
same result (F-M2.3-6 / 84.4 precedent re-applied).
"""


import hashlib
from dataclasses import dataclass, field
from typing import Callable, Mapping, Protocol


class BlobReader(Protocol):
    """The ONLY ambient seam: turn a relative path into raw bytes.

    Hermetic default (kickoff E / 84.4): a shipped supervisor NEVER calls the
    reader unless an explicit snapshot policy injects a reader and a sealed
    root. The guard is handed a reader; it does not discover one.
    """

    def __call__(self, relative_path: str) -> bytes: ...


@dataclass(frozen=True)
class PackageSnapshot:
    """A byte-frozen datum: relative path -> sha256 of the blob.

    This is an IMMUTABLE_ARTIFACT rung of evidence (evidence.py hierarchy):
    it outranks every narration. Nothing below can be re-derived from memory;
    it is a capture of the filesystem at a declared instant.
    """

    blob_hashes: Mapping[str, str] = field(default_factory=dict)
    sealed_at: str = ""

    @classmethod
    def capture(
        cls,
        relative_paths: tuple[str, ...],
        reader: BlobReader,
        sealed_at: str,
    ) -> "PackageSnapshot":
        hashes = {
            rel: hashlib.sha256(reader(rel)).hexdigest() for rel in relative_paths
        }
        return cls(blob_hashes=hashes, sealed_at=sealed_at)

    def folder_fingerprint(self) -> str:
        """Deterministic folder datum: sorted path->hash, hashed once.

        Same blob set (same order-insensitive content) -> same fingerprint,
        always. This is the seal compared on every guard check."""
        items = sorted(self.blob_hashes.items())
        joined = "|".join(f"{rel}={digest}" for rel, digest in items)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MutationReport:
    """Fresh datum after a guard re-measure (outcome, never a claim).

    `mutated=True` is the ONLY hard fact the supervisor consumes. The rest is
    forensic detail for the creator. A report is FRESH only while the
    snapshot policy + current blobs it was measured against are unchanged
    (stale-result invalidation, 84.4): any post-report mutation makes the
    report STALE by construction.
    """

    mutated: bool
    added: tuple[str, ...] = field(default_factory=tuple)
    removed: tuple[str, ...] = field(default_factory=tuple)
    changed: tuple[str, ...] = field(default_factory=tuple)
    detail: str = ""


class MutationGuard:
    """A sealed ratchet over a bytes set. Immutable once sealed.

    After `seal()`, the ONLY allowed operations are reads (`check`) and a
    NEW explicit `reopen()` (creator-gated concept: reopening the package
    begins a NEW task, it never weakly edits the frozen one).

    Post-PASS law (hard invariant, supervisor design): once a package is
    FROZEN_SUCCESS, any `check()` that reports `mutated=True` means the PASS
    datum is INVALIDATED - the acceptance is stale and the package must be
    re-classified FAILED before any further work (T18 regression beats this
    exact drift).
    """

    __slots__ = ("_snapshot",)

    def __init__(self, snapshot: PackageSnapshot | None = None) -> None:
        self._snapshot = snapshot

    @property
    def sealed(self) -> bool:
        return self._snapshot is not None

    def seal(self, snapshot: PackageSnapshot) -> None:
        """Irreversible-from-worker seal. One seal per guard lifetime.

        A guard that is already sealed may NOT be re-sealed by a worker
        (ratchet: the only un-seal is a creator-gated reopen as a NEW task).
        """
        if self.sealed:
            raise ValueError(
                "mutation guard already sealed; only a creator-gated REOPEN "
                "may start a new ratchet (never a worker re-seal)"
            )
        self._snapshot = snapshot

    def check(self, current: PackageSnapshot) -> MutationReport:
        """Compare a fresh capture against the sealed snapshot (hash datum).

        Same sealed + same current -> identical report (deterministic). The
        report is decided by BYTES, never narration: added = in current not
        sealed, removed = sealed not current, changed = hash drift.
        """
        if not self.sealed:
            raise ValueError("mutation guard is not sealed; cannot check")
        sealed = self._snapshot.blob_hashes
        current_map = current.blob_hashes
        added = tuple(sorted(set(current_map) - set(sealed)))
        removed = tuple(sorted(set(sealed) - set(current_map)))
        changed = tuple(
            sorted(
                rel
                for rel in set(sealed) & set(current_map)
                if sealed[rel] != current_map[rel]
            )
        )
        mutated = bool(added or removed or changed)
        detail = ""
        if mutated:
            parts = []
            if added:
                parts.append(f"added={','.join(added)}")
            if removed:
                parts.append(f"removed={','.join(removed)}")
            if changed:
                parts.append(f"changed={','.join(changed)}")
            detail = "POST-SEAL MUTATION: " + "; ".join(parts)
        else:
            detail = "sealed blob set byte-identical to snapshot"
        return MutationReport(
            mutated=mutated,
            added=added,
            removed=removed,
            changed=changed,
            detail=detail,
        )
