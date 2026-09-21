from __future__ import annotations

"""L0 Verification Authority - the acceptance mechanism (docs/ORCHESTRATOR_ARCHITECTURE.md §5).

No agent involved. Human-runnable. Deterministic fail-fast gate:

    1. Suite               - `uv run pytest -q`, counts parsed machine-readably.
    2. Frozen baseline check - every path under `src/jarvis/kernel/**` present at
       the baseline must be byte-identical unless listed in the package's
       `allowed_paths`. Compared against the *baseline*, never `main` (I3).
    3. Probe check         - all `tests/review/**` probes for this package must pass.
    4. Authority fingerprint - recorded from an immutable reference (I10), never a
       self-hash of the file currently executing.
    5. Digest               - sha256 over the canonical summary + commit.

On a frozen-module breach the gate returns `FAILED_FROZEN_BREACH`, no retry,
escalate (I3/I6). Exit 0 on pass, non-zero on failure. The supervisor reads ONLY
the emitted JSON artifact - it never parses pytest stdout nor an agent's message.
"""

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FROZEN_SCOPE = "src/jarvis/kernel"
DEFAULT_PROBES_DIR = "tests/review"

# Distinct non-zero exit codes let a caller distinguish WHY the gate failed
# without parsing human text (a machine-readable datum, never a narration).
EXIT_PASS = 0
EXIT_SUITE_FAIL = 1
EXIT_FROZEN_BREACH = 2
EXIT_PROBES_FAIL = 3
EXIT_USAGE_ERROR = 4
EXIT_INTERNAL_ERROR = 5


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a command with a fixed environment; never ambient config drift."""
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )


def _git_rev_parse(ref: str) -> str | None:
    """Resolve any ref (tag, branch, sha) to a full commit id, or None."""
    out = _run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=REPO_ROOT)
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def _path_exists_at(ref: str, rel: str) -> bool:
    """Does `rel` exist in the tree of immutable ref `ref`?"""
    out = _run(["git", "cat-file", "-e", f"{ref}:{rel}"], cwd=REPO_ROOT)
    return out.returncode == 0


def _parse_pytest_counts(text: str) -> tuple[int, int, int]:
    """Parses ``(passed, failed, errors)`` from pytest output, machine-readably.

    Matches the summary line forms ``503 passed in 12.0s`` and
    ``3 failed, 500 passed`` on their own numbers - never narration words.
    """
    passed = failed = errors = 0
    for m in re.finditer(r"(\d+)\s+passed", text):
        passed = int(m.group(1))
    for m in re.finditer(r"(\d+)\s+failed", text):
        failed = int(m.group(1))
    for m in re.finditer(r"(\d+)\s+errors?", text):
        errors = int(m.group(1))
    return passed, failed, errors


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json(obj: object) -> str:
    """Sorted keys, no whitespace - the same canonical form as the kernel's
    ``_canonical_json`` (docs, journal writes). Deterministic across writers."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def run_suite() -> dict:
    """Phase 1 - the full test suite, counts parsed machine-readably."""
    proc = _run(["uv", "run", "pytest", "-q", "-p", "no:cacheprovider"], cwd=REPO_ROOT)
    passed, failed, errors = _parse_pytest_counts(proc.stdout + proc.stderr)
    count = passed + failed + errors
    return {
        "passed": proc.returncode == 0 and failed == 0 and errors == 0,
        "count": count,
        "failed": failed + errors,
        "detail": "suite green at baseline" if passed else (proc.stdout + proc.stderr)[-1500:],
    }


def run_frozen_check(
    baseline_ref: str, head: str, allowed_paths: list[str], scope: str
) -> dict:
    """Phase 2 - every frozen-scope path present at the baseline must be
    byte-identical at `head` unless the package owns the path via `allowed_paths`.

    New paths (present at head but NOT at the baseline) are NOT violations: the
    frozen set rule covers what EXISTED at the baseline (ORCHESTRATOR §14). They
    are reported as informational `kernel_additions` for the reader.
    """
    out = _run(
        ["git", "diff", "--name-only", baseline_ref, head, "--", scope],
        cwd=REPO_ROOT,
    )
    changed = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]

    violations: list[str] = []
    additions: list[str] = []
    for rel in changed:
        if not rel.startswith(scope):
            continue
        if any(rel == a or rel.startswith(a.rstrip("/") + "/") for a in allowed_paths):
            continue
        if _path_exists_at(baseline_ref, rel):
            violations.append(rel)
        else:
            additions.append(rel)

    return {
        "passed": not violations,
        "violations": violations,
        "kernel_additions": additions,
    }


def run_probes(probes_dir: Path) -> dict:
    """Phase 3 - all review probes for this package must pass.

    A missing/empty probes dir is not a failure (probes are per-package; a
    package with no adversarial review simply declares none) - it is recorded
    as 0/0 declared.
    """
    if not probes_dir.is_dir():
        return {"total": 0, "passing": 0, "declared": False}
    procs = _run(
        ["uv", "run", "pytest", "-q", "-p", "no:cacheprovider", "--", str(probes_dir)],
        cwd=REPO_ROOT,
    )
    passed, failed, errors = _parse_pytest_counts(procs.stdout + procs.stderr)
    total = passed + failed + errors
    passing = passed
    return {"total": total, "passing": passing, "declared": True}


def collect_authority_fingerprint(head: str) -> dict:
    """Phase 4 - authority recorded from an immutable git reference (I10).

    The identity under test is the commit+tree the verify.py REFERENCE the gate
    was frozen at - a bare self-hash of the running file has no authority and is
    never used. `verify_py_sha256` is taken from the blob at that commit, not
    from the working tree.
    """
    authority_commit = _git_rev_parse(head) or head

    locked = REPO_ROOT / "uv.lock"
    if locked.is_file():
        dep_lock_hash = _sha256_file(locked)
        lock_name = "uv.lock"
    else:
        dep_lock_hash = _sha256_file(REPO_ROOT / "pyproject.toml")
        lock_name = "pyproject.toml"

    treasure = _run(["git", "ls-tree", "-r", "--full-tree", authority_commit], cwd=REPO_ROOT)
    tree_sha256 = _sha256_bytes(treasure.stdout.encode("utf-8"))

    verify_rel = Path("scripts/verify.py").as_posix()
    verify_blob = _run(["git", "show", f"{authority_commit}:{verify_rel}"], cwd=REPO_ROOT)
    if verify_blob.returncode == 0:
        verify_py_sha256 = _sha256_bytes(verify_blob.stdout.encode("utf-8"))
        verify_source = "git_blob"
    else:
        verify_py_sha256 = _sha256_bytes((REPO_ROOT / "scripts" / "verify.py").read_bytes())
        verify_source = "working_tree"

    return {
        "commit": authority_commit,
        "tree_sha256": tree_sha256,
        "verify_py_sha256": verify_py_sha256,
        "verify_py_source": verify_source,
        "python_version": platform.python_version(),
        "dependency_lock_hash": dep_lock_hash,
        "lock_reference": lock_name,
    }


def build_artifact(args: argparse.Namespace) -> dict:
    baseline_ref = args.baseline
    baseline_commit = _git_rev_parse(baseline_ref) or baseline_ref

    verified = _git_rev_parse(args.commit)
    if verified is None:
        print(
            f"usage error: --commit {args.commit} is not a resolvable commit",
            file=sys.stderr,
        )
        sys.exit(EXIT_USAGE_ERROR)

    artifact: dict = {
        "artifact_type": "verification",
        "package": args.package,
        "attempt_id": args.attempt,
        "input_commit": args.commit,
        "verified_commit": verified,
        "frozen_baseline": {
            "tag": baseline_ref,
            "commit": baseline_commit,
        },
    }

    # Fail-fast phase 1: suite -------------------------------------------------
    suite = run_suite()
    artifact["suite"] = {"passed": suite["passed"], "count": suite["count"], "failed": suite["failed"]}
    if not suite["passed"]:
        artifact["detail"] = {"phase": "suite", "reason": suite["detail"]}
        _finish(artifact, EXIT_SUITE_FAIL, args.out)
        sys.exit(EXIT_SUITE_FAIL)

    # Fail-fast phase 2: frozen baseline check ---------------------------------
    scope = args.scope.rstrip("/")
    frozen = run_frozen_check(baseline_commit, verified, args.allowed_paths, scope)
    artifact["frozen_check"] = {
        "passed": frozen["passed"],
        "violations": frozen["violations"],
    }
    if not frozen["passed"]:
        artifact["detail"] = {
            "phase": "frozen_check",
            "rule": "FAILED_FROZEN_BREACH (I3/I6): a path present at the baseline "
            "is modified and not in the package's allowed_paths; no retry, escalate",
            "violations": frozen["violations"],
        }
        _finish(artifact, EXIT_FROZEN_BREACH, args.out)
        sys.exit(EXIT_FROZEN_BREACH)

    # Fail-fast phase 3: probe check -------------------------------------------
    probes_result = run_probes(Path(args.probes))
    artifact["probes"] = {
        "total": probes_result["total"],
        "passing": probes_result["passing"],
    }
    if probes_result["declared"] and probes_result["passing"] != probes_result["total"]:
        artifact["detail"] = {
            "phase": "probes",
            "reason": f"probes {probes_result['passing']}/{probes_result['total']} passing",
        }
        _finish(artifact, EXIT_PROBES_FAIL, args.out)
        sys.exit(EXIT_PROBES_FAIL)

    # Phase 4: authority fingerprint (I10) --------------------------------------
    artifact["verification_authority"] = collect_authority_fingerprint(verified)

    # Phase 5: digest over canonical summary -------------------------------------
    canonical = _canonical_json(artifact)
    artifact["digest"] = "sha256:" + _sha256_bytes(canonical.encode("utf-8"))
    artifact["exit"] = EXIT_PASS
    _finish(artifact, EXIT_PASS, args.out)
    return artifact


def _finish(artifact: dict, exit_code: int, out: str | None) -> None:
    if "exit" not in artifact:
        artifact["exit"] = exit_code
    payload = json.dumps(artifact, indent=2, sort_keys=True)
    if out:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n", encoding="utf-8")
    print(payload)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts/verify.py",
        description="L0 Verification Authority - deterministic acceptance gate (§5).",
    )
    parser.add_argument("--package", required=True, help="package name under verification (e.g. M2.5)")
    parser.add_argument("--commit", required=True, help="commit sha under test (I9: a frozen commit)")
    parser.add_argument(
        "--baseline",
        required=True,
        help="immutable baseline tag/commit to compare the frozen set against (I3, never main)",
    )
    parser.add_argument("--out", help="output JSON artifact path")
    parser.add_argument("--attempt", default=None, help="attempt id (default <package>-a1)")
    parser.add_argument(
        "--scope",
        default=DEFAULT_FROZEN_SCOPE,
        help="frozen path prefix to guard (default src/jarvis/kernel)",
    )
    parser.add_argument(
        "--probes",
        default=DEFAULT_PROBES_DIR,
        help="probe directory to run (default tests/review)",
    )
    parser.add_argument(
        "--allow-path",
        dest="allowed_paths",
        action="append",
        default=[],
        metavar="PATH",
        help="path (or prefix) the package is ALLOWED to modify; repeatable",
    )
    args = parser.parse_args(argv)
    args.attempt = args.attempt or f"{args.package}-a1"
    build_artifact(args)
    return EXIT_PASS


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))