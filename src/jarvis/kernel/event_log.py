from __future__ import annotations

import asyncio
import datetime as _dt
import hashlib
import json
import os
import sqlite3
import threading
from typing import Any, AsyncIterator, Callable, Iterable, Mapping, Optional, Protocol

from pydantic import BaseModel, ConfigDict, Field


class EventLogError(RuntimeError):
    """Base error for the event log."""


class EventIntegrityError(EventLogError):
    """Typed integrity failure -- NAT-04 requires replay to halt on this."""


class Clock(Protocol):
    def now_utc_iso(self) -> str: ...


class SystemClock:
    def now_utc_iso(self) -> str:
        return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid(now_ms: Optional[int] = None) -> str:
    from datetime import timezone

    if now_ms is None:
        now_ms = int(_dt.datetime.now(timezone.utc).timestamp() * 1000)
    rnd = int.from_bytes(os.urandom(10), "big")
    value = (now_ms << 80) | rnd
    chars: list[str] = []
    for _ in range(26):
        chars.append(ULID_ALPHABET[value & 0b11111])
        value >>= 5
    return "".join(reversed(chars))


class Event(BaseModel):
    """Logical event per spec §85.1. Physical hashes are filled by the store."""

    model_config = ConfigDict(extra="forbid")

    event_id: Optional[str] = None
    stream_id: str
    stream_seq: Optional[int] = None
    ts_utc: Optional[str] = None
    event_type: str
    schema_version: int = 1
    principal_id: str
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    cause_event_id: Optional[str] = None
    correlation_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    actor_model: Optional[str] = None
    payload_sha256: Optional[str] = None
    prev_event_sha256: Optional[str] = None
    event_sha256: Optional[str] = None

    def chain_record(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "stream_id": self.stream_id,
            "stream_seq": self.stream_seq,
            "ts_utc": self.ts_utc,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "principal_id": self.principal_id,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "cause_event_id": self.cause_event_id,
            "correlation_id": self.correlation_id,
            "payload_sha256": self.payload_sha256,
            "prev_event_sha256": self.prev_event_sha256,
            "actor_model": self.actor_model,
        }

    def compute_event_sha256(self) -> str:
        if self.payload_sha256 is None:
            raise EventLogError("payload_sha256 must be set before event hash computation")
        return _sha256(_canonical_json(self.chain_record()))

    def compute_payload_sha256(self) -> str:
        return _sha256(_canonical_json(self.payload))


class EventLog:
    """Append-only, hash-chained event store. SQLite WAL, per ADR-005."""

    def __init__(
        self,
        db_path: str | os.PathLike[str] | None = None,
        clock: Clock | None = None,
        *,
        autocommit: bool = True,
    ) -> None:
        if db_path is None:
            home = os.environ.get("JARVIS_HOME", "~/.jarvis")
            db_path = os.path.join(os.path.expanduser(home), "log.db")
        self.db_path = os.fspath(db_path)
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._clock: Clock = clock or SystemClock()
        self._autocommit = autocommit
        self._write_lock = threading.RLock()
        self._conn = self._connect()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    stream_id TEXT NOT NULL,
                    stream_seq INTEGER NOT NULL,
                    ts_utc TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    principal_id TEXT NOT NULL,
                    mission_id TEXT,
                    task_id TEXT,
                    cause_event_id TEXT,
                    correlation_id TEXT,
                    payload_json TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    prev_event_sha256 TEXT,
                    event_sha256 TEXT NOT NULL,
                    actor_model TEXT,
                    UNIQUE (stream_id, stream_seq)
                );
                CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
                CREATE INDEX IF NOT EXISTS idx_events_mission ON events(mission_id);
                CREATE TRIGGER IF NOT EXISTS events_no_update
                BEFORE UPDATE ON events
                BEGIN
                    SELECT RAISE(ABORT, 'append-only: update forbidden');
                END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete
                BEFORE DELETE ON events
                BEGIN
                    SELECT RAISE(ABORT, 'append-only: delete forbidden');
                END;
                """
            )

    def _last_event(self) -> Optional[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT event_sha256 FROM events ORDER BY seq DESC LIMIT 1"
        )
        return cur.fetchone()

    def _next_stream_seq(self, stream_id: str) -> int:
        cur = self._conn.execute(
            "SELECT COALESCE(MAX(stream_seq), 0) + 1 AS nxt FROM events WHERE stream_id = ?",
            (stream_id,),
        )
        return int(cur.fetchone()["nxt"])

    def append(self, event: Event | Mapping[str, Any]) -> str:
        """Append one event. Returns the ULID event id."""
        if not isinstance(event, Event):
            event = Event(**event)

        if event.event_id is None:
            event = event.model_copy(update={"event_id": new_ulid()})
        if event.ts_utc is None:
            event = event.model_copy(update={"ts_utc": self._clock.now_utc_iso()})

        payload_sha = event.compute_payload_sha256()
        with self._write_lock:
            try:
                with self._conn:
                    event = event.model_copy(
                        update={
                            "stream_seq": self._next_stream_seq(event.stream_id),
                            "payload_sha256": payload_sha,
                        }
                    )
                    prev = self._last_event()
                    event = event.model_copy(
                        update={
                            "prev_event_sha256": prev["event_sha256"] if prev else None,
                        }
                    )
                    event = event.model_copy(
                        update={"event_sha256": event.compute_event_sha256()}
                    )
                    self._conn.execute(
                        """
                        INSERT INTO events (
                            event_id, stream_id, stream_seq, ts_utc, event_type,
                            schema_version, principal_id, mission_id, task_id,
                            cause_event_id, correlation_id, payload_json,
                            payload_sha256, prev_event_sha256, event_sha256, actor_model
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event.event_id,
                            event.stream_id,
                            event.stream_seq,
                            event.ts_utc,
                            event.event_type,
                            event.schema_version,
                            event.principal_id,
                            event.mission_id,
                            event.task_id,
                            event.cause_event_id,
                            event.correlation_id,
                            _canonical_json(event.payload).decode("utf-8"),
                            event.payload_sha256,
                            event.prev_event_sha256,
                            event.event_sha256,
                            event.actor_model,
                        ),
                    )
            except sqlite3.IntegrityError as exc:
                raise EventLogError(f"append rejected: {exc}") from exc
        return event.event_id  # type: ignore[return-value]

    def _build_query(self, since: int, event_type: str | None, stream_id: str | None, mission_id: str | None) -> tuple[str, list[Any]]:
        clauses = ["seq > ?"]
        params: list[Any] = [since]
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type)
        if stream_id is not None:
            clauses.append("stream_id = ?")
            params.append(stream_id)
        if mission_id is not None:
            clauses.append("mission_id = ?")
            params.append(mission_id)
        where = " AND ".join(clauses)
        return f"SELECT * FROM events WHERE {where} ORDER BY seq ASC", params

    def _rows_to_events(self, rows: Iterable[sqlite3.Row]) -> list[Event]:
        events: list[Event] = []
        for row in rows:
            events.append(
                Event(
                    event_id=row["event_id"],
                    stream_id=row["stream_id"],
                    stream_seq=row["stream_seq"],
                    ts_utc=row["ts_utc"],
                    event_type=row["event_type"],
                    schema_version=row["schema_version"],
                    principal_id=row["principal_id"],
                    mission_id=row["mission_id"],
                    task_id=row["task_id"],
                    cause_event_id=row["cause_event_id"],
                    correlation_id=row["correlation_id"],
                    payload=json.loads(row["payload_json"]),
                    actor_model=row["actor_model"],
                    payload_sha256=row["payload_sha256"],
                    prev_event_sha256=row["prev_event_sha256"],
                    event_sha256=row["event_sha256"],
                )
            )
        return events

    def stream(
        self,
        since: int = 0,
        event_type: str | None = None,
        stream_id: str | None = None,
        mission_id: str | None = None,
    ) -> AsyncIterator[Event]:
        """Read events after `since` (global seq) in global order."""
        return self._stream_inner(since, event_type, stream_id, mission_id)

    async def _stream_inner(
        self, since: int, event_type: str | None, stream_id: str | None, mission_id: str | None
    ) -> AsyncIterator[Event]:
        sql, params = self._build_query(since, event_type, stream_id, mission_id)
        rows = await asyncio.to_thread(
            lambda: self._conn.execute(sql, params).fetchall()
        )
        for event in self._rows_to_events(rows):
            yield event

    def verify_chain(self) -> bool:
        """Recompute payload + chain hashes for every event. NAT-04 evidence."""
        cur = self._conn.execute(
            "SELECT * FROM events ORDER BY seq ASC"
        )
        rows = cur.fetchall()
        prev_hash: str | None = None
        for row in rows:
            payload = json.loads(row["payload_json"])
            payload_sha = _sha256(_canonical_json(payload))
            if payload_sha != row["payload_sha256"]:
                return False
            if row["prev_event_sha256"] != prev_hash:
                return False
            event = self._rows_to_events([row])[0]
            if event.compute_event_sha256() != row["event_sha256"]:
                return False
            prev_hash = row["event_sha256"]
        return True

    def replay(self, since: int = 0) -> list[Event]:
        """Deterministic replay in global order. Always verifies; halts on
        integrity failure (NAT-04). There is deliberately no unchecked caller
        path in production."""
        sql, params = self._build_query(since, None, None, None)
        rows = self._conn.execute(sql, params).fetchall()

        prev_hash: str | None = None
        if prev := self._conn.execute("SELECT event_sha256 FROM events WHERE seq <= ? ORDER BY seq DESC LIMIT 1", (since,)).fetchone():
            prev_hash = prev["event_sha256"]

        for row in rows:
            payload = json.loads(row["payload_json"])
            if _sha256(_canonical_json(payload)) != row["payload_sha256"]:
                raise EventIntegrityError(
                    f"payload hash mismatch at seq={row['seq']} (event_id={row['event_id']})"
                )
            if row["prev_event_sha256"] != prev_hash:
                raise EventIntegrityError(
                    f"chain hash mismatch at seq={row['seq']} (event_id={row['event_id']})"
                )
            event = self._rows_to_events([row])[0]
            if event.compute_event_sha256() != row["event_sha256"]:
                raise EventIntegrityError(
                    f"event hash mismatch at seq={row['seq']} (event_id={row['event_id']})"
                )
            prev_hash = row["event_sha256"]
        return self._rows_to_events(rows)

    def _read_all_events_unchecked(self, since: int = 0) -> list[Event]:
        """Tests-only: read events without integrity checks. Production callers
        must use replay() and always verify."""
        sql, params = self._build_query(since, None, None, None)
        rows = self._conn.execute(sql, params).fetchall()
        return self._rows_to_events(rows)

    def projection_digest(self) -> str:
        """INTERIM NAT-03 proxy: byte-identical, deterministic digest over the
        replayed event stream. MUST be replaced by a digest over projection
        state once the minimal memory projection lands (spec §134.1 MUST list,
        NAT-03 requires hashing the projection, not the raw event stream)."""
        h = hashlib.sha256()
        for event in self.replay():
            record = {
                "_event": event.chain_record(),
                "payload": event.payload,
            }
            h.update(_canonical_json(record))
        return h.hexdigest()

    def last_seq(self) -> int:
        row = self._conn.execute("SELECT COALESCE(MAX(seq), 0) AS s FROM events").fetchone()
        return int(row["s"])

    def close(self) -> None:
        self._conn.close()