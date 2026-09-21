#!/usr/bin/env python3
from __future__ import annotations

"""Thin deterministic supervisor driver (ORCHESTRATOR_ARCHITECTURE.md §11).

Wires the deterministic control pieces together and invents no capabilities.
Worker dispatch / model calls are out of scope here; this proves the loop:
lock -> read state -> verify -> evidence bundle -> ledger -> journal.

Commands:
  init             create the state dir, ledger, registry skeleton
  status           show lock + ledger + journal tail
  verify <pkg>     run L0 scripts/verify.py, write the evidence bundle,
                   update the ledger, append a journal record
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from journal import Journal  # noqa: E402


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Supervisor:
    def __init__(self, state_dir: Path, repo: Path) -> None:
        self.state = state_dir
        self.repo = repo
        self.state.mkdir(parents=True, exist_ok=True)
        self.journal = Journal(self.state / "journal.jsonl")
        self.ledger_path = self.state / "ledger.json"
        self.lock_path = self.state / "supervisor.lock"
        self.evidence_dir = self.state / "evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.instance = "sup-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    # ---- single-writer lock (§2) -------------------------------------
    def acquire(self, ttl: int = 3600, force: bool = False) -> None:
        if self.lock_path.exists() and not force:
            try:
                data = json.loads(self.lock_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            if data.get("expires_at", 0) > time.time():
                raise RuntimeError(
                    f"another supervisor holds the lock: {data.get('supervisor_instance_id')}"
                )
        self.lock_path.write_text(json.dumps({
            "supervisor_instance_id": self.instance,
            "started_at": time.time(),
            "expires_at": time.time() + ttl,
        }, indent=2), encoding="utf-8")

    def release(self) -> None:
        if self.lock_path.exists():
            self.lock_path.unlink()

    # ---- durable ledger (§2) -----------------------------------------
    def load_ledger(self) -> dict:
        if not self.ledger_path.exists():
            return {}
        return json.loads(self.ledger_path.read_text(encoding="utf-8"))

    def save_ledger(self, ledger: dict) -> None:
        self.ledger_path.write_text(
            json.dumps(ledger, indent=2, sort_keys=True), encoding="utf-8"
        )

    # ---- acceptance step (§8 steps 14-18) ----------------------------
    def verify(
        self,
        package: str,
        baseline: str,
        allow: list[str],
        frozen_root: str | None,
        commit: str | None = None,
    ) -> int:
        out = self.evidence_dir / f"{package}.json"
        commit_sha = commit or subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(self.repo), text=True
        ).strip()
        cmd = [
            sys.executable,
            str(self.repo / "scripts" / "verify.py"),
            "--package", package,
            "--commit", commit_sha,
            "--baseline", baseline,
            "--out", str(out),
        ]
        for p in allow:
            cmd += ["--allow-path", p]
        if frozen_root:
            cmd += ["--scope", frozen_root]
        rc = subprocess.call(cmd)

        ledger = self.load_ledger()
        ledger.setdefault("frozen_packages", [])
        ledger["current_milestone"] = package
        ledger["last_verify_exit"] = rc
        if rc == 0 and out.exists():
            bundle = json.loads(out.read_text(encoding="utf-8"))
            ledger["baseline_commit"] = bundle.get("frozen_baseline", {}).get("commit")
            ledger["current_commit"] = bundle.get("verified_commit")
            ledger["last_known_good"] = bundle.get("verified_commit")
            if package not in ledger["frozen_packages"]:
                ledger["frozen_packages"].append(package)
            self.journal.append({"event": "ACCEPT", "package": package, "exit": rc,
                                 "digest": bundle.get("digest")})
        else:
            self.journal.append({"event": "REJECT", "package": package, "exit": rc})
        self.save_ledger(ledger)
        return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="JARVIS thin supervisor driver")
    ap.add_argument("--state", default=os.environ.get("JARVIS_ORCHESTRATOR_STATE", r"F:\JARVIS_ORCHESTRATOR_STATE"))
    ap.add_argument("--repo", default=os.environ.get("JARVIS_REPO", r"F:\JARVIS2.0"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    v = sub.add_parser("verify")
    v.add_argument("package")
    v.add_argument("--baseline", required=True)
    v.add_argument("--commit", default=None, help="commit under test (default: current HEAD)")
    v.add_argument("--allow", action="append", default=[])
    v.add_argument("--frozen-root", default=None)
    args = ap.parse_args(argv)

    sup = Supervisor(Path(args.state), Path(args.repo))

    if args.cmd == "init":
        sup.acquire(force=True)
        sup.save_ledger({
            "current_milestone": None, "baseline_commit": None,
            "current_commit": None, "last_known_good": None,
            "filesystem_generation": 0, "verification_generation": 0,
            "authority_level": "L0", "frozen_packages": [],
            "current_blocker": None, "next_safe_step": "choose next milestone",
        })
        sup.journal.append({"event": "SUPERVISOR_INIT", "instance": sup.instance})
        sup.release()
        print("supervisor: init OK")
        return 0

    if args.cmd == "status":
        ledger = sup.load_ledger()
        tail = sup.journal.replay()[-3:]
        print(json.dumps({"ledger": ledger, "journal_tail": tail}, indent=2))
        return 0

    if args.cmd == "verify":
        sup.acquire()
        try:
            return sup.verify(
                args.package,
                args.baseline,
                args.allow,
                args.frozen_root,
                commit=args.commit,
            )
        finally:
            sup.release()

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
