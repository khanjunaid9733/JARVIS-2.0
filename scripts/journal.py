#!/usr/bin/env python3
from __future__ import annotations

"""L1 Journal (ORCHESTRATOR_ARCHITECTURE.md §6).

Append-only, hash-chained, durable (fsync per record). JSONL is the current
storage; the contract is the five semantics: JournalRecord, Append, Replay,
Hash-chain, Durability. `replay()` verifies the chain and raises on tamper.
"""

import datetime
import hashlib
import json
import os
import sys
import time
from pathlib import Path


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class JournalIntegrityError(RuntimeError):
    """Raised when the hash chain does not verify (tamper or corruption)."""


class Journal:
    GENESIS = "0" * 64

    def __init__(self, path: str | os.PathLike) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _lines(self) -> list[str]:
        if not self.path.exists():
            return []
        return [ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def append(self, record: dict, *, ts: str | None = None) -> dict:
        lines = self._lines()
        prev = self.GENESIS
        seq = 0
        if lines:
            last = json.loads(lines[-1])
            prev = last["hash"]
            seq = int(last["seq"]) + 1
        entry = {
            "seq": seq,
            "ts": ts or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "prev": prev,
            "record": record,
        }
        entry["hash"] = _sha256(_canonical(entry))
        line = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return entry

    def replay(self) -> list[dict]:
        out: list[dict] = []
        prev = self.GENESIS
        for i, ln in enumerate(self._lines()):
            entry = json.loads(ln)
            if entry.get("seq") != i:
                raise JournalIntegrityError(f"seq gap at line {i}: got {entry.get('seq')!r}")
            if entry.get("prev") != prev:
                raise JournalIntegrityError(f"chain break at seq {entry.get('seq')}")
            claimed = entry.pop("hash", None)
            actual = _sha256(_canonical(entry))
            entry["hash"] = claimed
            if claimed != actual:
                raise JournalIntegrityError(f"hash mismatch at seq {entry.get('seq')}")
            prev = claimed
            out.append(entry)
        return out

    def last(self) -> dict | None:
        entries = self.replay()
        return entries[-1] if entries else None


def _selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        j = Journal(Path(td) / "j.jsonl")
        j.append({"event": "A"})
        j.append({"event": "B"})
        r = j.replay()
        assert len(r) == 2 and r[0]["record"]["event"] == "A", "append/replay"
        p = Path(td) / "j.jsonl"
        lines = p.read_text(encoding="utf-8").splitlines()
        lines[0] = lines[0].replace('"A"', '"X"')
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            j.replay()
        except JournalIntegrityError:
            print("journal: SELFTEST OK (append, replay, tamper-detected)")
            return 0
        print("journal: SELFTEST FAIL (tamper not detected)")
        return 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
