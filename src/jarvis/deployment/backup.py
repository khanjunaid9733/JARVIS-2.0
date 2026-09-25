"""Automated Backup, Disaster Recovery (DR) & Self-Healing for JARVIS 2.0.

Provides:
- LedgerBackupManager: Online SQLite backup via conn.backup() without write stalls.
- SHA-256 verification export manifests for disaster recovery.
- Integrity verification: Replays restored databases and asserts hash chain integrity.
- Self-healing WAL checkpointing: PRAGMA wal_checkpoint(TRUNCATE).
- Automatic snapshot rotation and retention.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..kernel.event_log import (
    Event,
    EventIntegrityError,
    EventLog,
    EventLogError,
    _canonical_json,
    new_ulid,
)


@dataclass(frozen=True)
class CheckpointStats:
    busy: int
    log: int
    checkpointed: int


@dataclass(frozen=True)
class BackupManifest:
    backup_id: str
    created_at: str
    source_db_path: str
    backup_file_path: str
    manifest_file_path: str
    file_size_bytes: int
    db_sha256: str
    last_seq: int
    event_count: int
    projection_digest: str
    wal_checkpointed: bool
    label: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackupManifest:
        return cls(**data)


def _compute_file_sha256(path: Path | str) -> str:
    """Calculate the SHA-256 hex digest of a file on disk."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class LedgerBackupManager:
    """Manages automated online backups, verification, and disaster recovery."""

    def __init__(
        self,
        event_log: Optional[EventLog] = None,
        db_path: Optional[str | Path] = None,
        backup_dir: Optional[str | Path] = None,
        max_retained_backups: int = 10,
    ) -> None:
        self._event_log = event_log
        if event_log is not None:
            self._db_path = Path(event_log.db_path).resolve()
        elif db_path is not None:
            self._db_path = Path(db_path).resolve()
        else:
            home = os.environ.get("JARVIS_HOME", "~/.jarvis")
            self._db_path = Path(os.path.expanduser(home)).resolve() / "log.db"

        if backup_dir is not None:
            self._backup_dir = Path(backup_dir).resolve()
        else:
            self._backup_dir = self._db_path.parent / "backups"

        self._max_retained_backups = max_retained_backups
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def backup_dir(self) -> Path:
        return self._backup_dir

    def checkpoint_wal(self) -> CheckpointStats:
        """Perform self-healing WAL checkpoint with TRUNCATE mode.
        
        Flushes all outstanding WAL pages into the main SQLite database file
        and truncates the WAL file to zero bytes.
        """
        if not self._db_path.exists():
            return CheckpointStats(busy=0, log=0, checkpointed=0)

        conn = sqlite3.connect(str(self._db_path), timeout=10.0)
        try:
            cursor = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            row = cursor.fetchone()
            # row: (busy, log, checkpointed)
            stats = CheckpointStats(
                busy=int(row[0]),
                log=int(row[1]),
                checkpointed=int(row[2]),
            )
            return stats
        finally:
            conn.close()

    def create_backup(
        self,
        label: Optional[str] = None,
        checkpoint: bool = True,
    ) -> BackupManifest:
        """Creates an atomic, non-blocking online backup of the ledger.
        
        1. Optionally runs PRAGMA wal_checkpoint(TRUNCATE).
        2. Copies state via SQLite online backup API (source_conn.backup()).
        3. Computes disk file SHA-256 digest.
        4. Replays the backup copy with EventLog to verify hash chain integrity.
        5. Saves manifest JSON sidecar.
        6. Emits system.backup.created event to event log if available.
        7. Enforces backup rotation.
        """
        if not self._db_path.exists():
            raise FileNotFoundError(f"Source database not found at {self._db_path}")

        wal_checkpointed = False
        if checkpoint:
            try:
                self.checkpoint_wal()
                wal_checkpointed = True
            except Exception:
                wal_checkpointed = False

        backup_id = f"backup_{new_ulid()}"
        backup_filename = f"{backup_id}.db"
        backup_file_path = self._backup_dir / backup_filename
        manifest_file_path = self._backup_dir / f"{backup_id}.manifest.json"

        # Safe SQLite online backup
        source_conn = sqlite3.connect(str(self._db_path), timeout=30.0)
        dest_conn = sqlite3.connect(str(backup_file_path))
        try:
            with dest_conn:
                source_conn.backup(dest_conn, pages=100)
        finally:
            dest_conn.close()
            source_conn.close()

        # Compute SHA-256 of backup file
        file_size = backup_file_path.stat().st_size
        db_sha256 = _compute_file_sha256(backup_file_path)

        # Verify backup integrity via EventLog replay
        verify_log = EventLog(db_path=backup_file_path)
        try:
            events = verify_log.replay()
            last_seq = verify_log.last_seq()
            projection_digest = verify_log.projection_digest()
            event_count = len(events)
        finally:
            verify_log.close()

        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        manifest = BackupManifest(
            backup_id=backup_id,
            created_at=now_iso,
            source_db_path=str(self._db_path),
            backup_file_path=str(backup_file_path),
            manifest_file_path=str(manifest_file_path),
            file_size_bytes=file_size,
            db_sha256=db_sha256,
            last_seq=last_seq,
            event_count=event_count,
            projection_digest=projection_digest,
            wal_checkpointed=wal_checkpointed,
            label=label,
        )

        # Write manifest sidecar
        with open(manifest_file_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, sort_keys=True)

        # Emit event if live event log is active
        if self._event_log is not None:
            try:
                self._event_log.append(
                    Event(
                        stream_id="system.backup",
                        event_type="system.backup.created",
                        principal_id="system.backup_manager",
                        payload={
                            "backup_id": backup_id,
                            "db_sha256": db_sha256,
                            "last_seq": last_seq,
                            "event_count": event_count,
                            "projection_digest": projection_digest,
                            "label": label,
                        },
                    )
                )
            except Exception:
                pass

        # Rotate old backups
        self.rotate_backups()
        return manifest

    def _resolve_paths(self, backup_id_or_path: str | Path) -> tuple[Path, Path]:
        """Resolves target backup .db and .manifest.json paths."""
        p = Path(backup_id_or_path)
        if p.is_file():
            if p.suffix == ".json":
                manifest_path = p
                db_path = p.with_suffix("").with_suffix(".db")
            else:
                db_path = p
                manifest_path = p.with_suffix(".manifest.json")
        else:
            # Assume backup_id string
            bid = str(backup_id_or_path)
            db_path = self._backup_dir / f"{bid}.db"
            manifest_path = self._backup_dir / f"{bid}.manifest.json"

        if not db_path.exists():
            raise FileNotFoundError(f"Backup database file not found: {db_path}")
        if not manifest_path.exists():
            raise FileNotFoundError(f"Backup manifest file not found: {manifest_path}")

        return db_path, manifest_path

    def load_manifest(self, backup_id_or_path: str | Path) -> BackupManifest:
        _, manifest_path = self._resolve_paths(backup_id_or_path)
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return BackupManifest.from_dict(data)

    def list_backups(self) -> list[BackupManifest]:
        """Returns all valid backups in backup directory, newest first."""
        manifests: list[BackupManifest] = []
        for mf in self._backup_dir.glob("*.manifest.json"):
            try:
                with open(mf, "r", encoding="utf-8") as f:
                    manifests.append(BackupManifest.from_dict(json.load(f)))
            except Exception:
                continue
        manifests.sort(key=lambda m: m.created_at, reverse=True)
        return manifests

    def verify_backup(self, backup_id_or_path: str | Path) -> bool:
        """Verifies integrity of a backup file against its manifest.
        
        1. Checks SHA-256 disk checksum.
        2. Replays EventLog verifying all event hashes and chain continuity.
        3. Validates projection digest matches.
        4. Emits system.backup.verified event.
        """
        db_path, manifest_path = self._resolve_paths(backup_id_or_path)
        manifest = self.load_manifest(manifest_path)

        # Check disk checksum
        actual_sha = _compute_file_sha256(db_path)
        if actual_sha != manifest.db_sha256:
            raise EventIntegrityError(
                f"Backup SHA-256 checksum mismatch for {manifest.backup_id}: "
                f"expected {manifest.db_sha256}, got {actual_sha}"
            )

        # Replay event chain
        verify_log = EventLog(db_path=db_path)
        try:
            verify_log.replay()
            actual_digest = verify_log.projection_digest()
            if actual_digest != manifest.projection_digest:
                raise EventIntegrityError(
                    f"Projection digest mismatch for {manifest.backup_id}: "
                    f"expected {manifest.projection_digest}, got {actual_digest}"
                )
        finally:
            verify_log.close()

        # Emit verification event if live event log is active
        if self._event_log is not None:
            try:
                self._event_log.append(
                    Event(
                        stream_id="system.backup",
                        event_type="system.backup.verified",
                        principal_id="system.backup_manager",
                        payload={
                            "backup_id": manifest.backup_id,
                            "verified": True,
                        },
                    )
                )
            except Exception:
                pass

        return True

    def restore_backup(
        self,
        backup_id_or_path: str | Path,
        target_db_path: Optional[str | Path] = None,
        overwrite: bool = False,
    ) -> EventLog:
        """Restores a backup database for disaster recovery.
        
        1. Performs full verification of the backup before attempting restore.
        2. Checks target path and respects overwrite flag.
        3. Copies backup database file and removes stale WAL journals.
        4. Replays restored EventLog to ensure restored integrity.
        5. Emits system.backup.restored event if live log is attached.
        6. Returns the operational restored EventLog instance.
        """
        db_path, manifest_path = self._resolve_paths(backup_id_or_path)
        manifest = self.load_manifest(manifest_path)

        # Step 1: Pre-restore verification
        self.verify_backup(manifest_path)

        target = Path(target_db_path).resolve() if target_db_path else self._db_path
        if target.exists() and not overwrite:
            raise FileExistsError(
                f"Cannot restore: target database already exists at {target} and overwrite=False"
            )

        target.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing target and any leftover WAL/SHM sidecars
        if target.exists():
            target.unlink()
        wal_sidecar = target.with_name(f"{target.name}-wal")
        if wal_sidecar.exists():
            wal_sidecar.unlink()
        shm_sidecar = target.with_name(f"{target.name}-shm")
        if shm_sidecar.exists():
            shm_sidecar.unlink()

        # Copy database file
        shutil.copy2(db_path, target)

        # Step 2: Post-restore verification
        restored_log = EventLog(db_path=target)
        try:
            restored_log.replay()
            restored_digest = restored_log.projection_digest()
            if restored_digest != manifest.projection_digest:
                restored_log.close()
                raise EventIntegrityError(
                    f"Restored database projection digest mismatch: "
                    f"expected {manifest.projection_digest}, got {restored_digest}"
                )
        except Exception:
            restored_log.close()
            raise

        if self._event_log is not None:
            try:
                self._event_log.append(
                    Event(
                        stream_id="system.backup",
                        event_type="system.backup.restored",
                        principal_id="system.backup_manager",
                        payload={
                            "backup_id": manifest.backup_id,
                            "restored_to": str(target),
                        },
                    )
                )
            except Exception:
                pass

        return restored_log

    def rotate_backups(self) -> list[str]:
        """Prunes backups exceeding max_retained_backups. Returns pruned backup IDs."""
        manifests = self.list_backups()
        if len(manifests) <= self._max_retained_backups:
            return []

        to_prune = manifests[self._max_retained_backups :]
        pruned_ids: list[str] = []
        for m in to_prune:
            db_p = Path(m.backup_file_path)
            mf_p = Path(m.manifest_file_path)
            try:
                if db_p.exists():
                    db_p.unlink()
                if mf_p.exists():
                    mf_p.unlink()
                pruned_ids.append(m.backup_id)
            except Exception:
                continue

        return pruned_ids
