from __future__ import annotations

"""M2.5 - mutation_guard: the post-PASS file mutation detector (84.4).

The guard reads BYTES and compares HASHES. It never asks the worker "did you
change anything?" - a narration can never veto the byte datum. Same sealed
snapshot + same current blobs -> identical report (deterministic). Clocks and
the filesystem are injected seams (BlobReader), never ambient. Hermetic: this
file performs no I/O except through the injected reader.
"""

import hashlib

import pytest

from jarvis.supervisor import (
    BlobReader,
    MutationGuard,
    MutationReport,
    PackageSnapshot,
)

ISO = "2026-09-21T00:00:00.000Z"


def _reader_for(blobs: dict[str, bytes]) -> BlobReader:
    def reader(relative_path: str) -> bytes:
        return blobs[relative_path]

    return reader


def test_capture_hashes_blobs_through_injected_reader() -> None:
    blobs = {"a.py": b"def a(): return 1", "b.py": b"def b(): return 2"}
    snap = PackageSnapshot.capture(
        relative_paths=("a.py", "b.py"),
        reader=_reader_for(blobs),
        sealed_at=ISO,
    )
    assert snap.blob_hashes["a.py"] == hashlib.sha256(blobs["a.py"]).hexdigest()
    assert snap.blob_hashes["b.py"] == hashlib.sha256(blobs["b.py"]).hexdigest()
    assert snap.sealed_at == ISO


def test_folder_fingerprint_is_order_independent_and_deterministic() -> None:
    a = PackageSnapshot(blob_hashes={"x": "1", "y": "2"}, sealed_at=ISO)
    b = PackageSnapshot(blob_hashes={"y": "2", "x": "1"}, sealed_at=ISO)
    c = PackageSnapshot(blob_hashes={"x": "1", "y": "3"}, sealed_at=ISO)
    assert a.folder_fingerprint() == b.folder_fingerprint()
    assert a.folder_fingerprint() == a.folder_fingerprint()
    assert a.folder_fingerprint() != c.folder_fingerprint()


def test_seal_then_check_identical_blobs_is_not_mutated() -> None:
    blobs = {"a.py": b"same", "b.py": b"same2"}
    snap = PackageSnapshot.capture(
        relative_paths=("a.py", "b.py"),
        reader=_reader_for(blobs),
        sealed_at=ISO,
    )
    guard = MutationGuard()
    guard.seal(snap)
    assert guard.sealed is True

    report = guard.check(current=snap)
    assert isinstance(report, MutationReport)
    assert report.mutated is False
    assert report.added == ()
    assert report.removed == ()
    assert report.changed == ()


def test_added_removed_and_changed_are_reported() -> None:
    sealed = PackageSnapshot(
        blob_hashes={"a.py": "h-a", "b.py": "h-b"},
        sealed_at=ISO,
    )
    current = PackageSnapshot(
        blob_hashes={"b.py": "h-b", "c.py": "h-c"},  # a removed, c added, b same
        sealed_at=ISO,
    )
    guard = MutationGuard()
    guard.seal(sealed)
    report = guard.check(current=current)
    assert report.mutated is True
    assert report.removed == ("a.py",)
    assert report.added == ("c.py",)
    assert report.changed == ()


def test_hash_drift_is_a_change_even_when_paths_match() -> None:
    sealed = PackageSnapshot(blob_hashes={"a.py": "h-old"}, sealed_at=ISO)
    current = PackageSnapshot(blob_hashes={"a.py": "h-new"}, sealed_at=ISO)
    guard = MutationGuard()
    guard.seal(sealed)
    report = guard.check(current=current)
    assert report.mutated is True
    assert report.changed == ("a.py",)
    assert "POST-SEAL MUTATION" in report.detail


def test_identical_after_seal_has_clean_detail() -> None:
    guard = MutationGuard()
    guard.seal(PackageSnapshot(blob_hashes={"a.py": "h"}, sealed_at=ISO))
    report = guard.check(current=PackageSnapshot(blob_hashes={"a.py": "h"}, sealed_at=ISO))
    assert report.mutated is False
    assert "byte-identical" in report.detail


def test_check_before_seal_raises() -> None:
    guard = MutationGuard()
    with pytest.raises(ValueError):
        guard.check(current=PackageSnapshot(blob_hashes={}, sealed_at=ISO))


def test_reseal_raises_once_sealed() -> None:
    """A guard already sealed may NOT be re-sealed by a worker (ratchet: the
    only un-seal is a creator-gated reopen as a NEW task)."""
    guard = MutationGuard()
    guard.seal(PackageSnapshot(blob_hashes={"a.py": "h1"}, sealed_at=ISO))
    with pytest.raises(ValueError):
        guard.seal(PackageSnapshot(blob_hashes={"a.py": "h2"}, sealed_at=ISO))


def test_same_inputs_produce_identical_report() -> None:
    sealed = PackageSnapshot(blob_hashes={"a.py": "h-sealed"}, sealed_at=ISO)
    current = PackageSnapshot(blob_hashes={"a.py": "h-drifted"}, sealed_at=ISO)
    guard = MutationGuard()
    guard.seal(sealed)
    r1 = guard.check(current=current)
    r2 = guard.check(current=current)
    assert r1 == r2
    assert r1.mutated is r2.mutated is True
    assert r1.changed == r2.changed == ("a.py",)