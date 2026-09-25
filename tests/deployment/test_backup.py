"""Tests for Automated Backup, Disaster Recovery & Self-Healing (Milestone M6.5)."""

import os
from pathlib import Path
import pytest

from jarvis.deployment.backup import (
    BackupManifest,
    CheckpointStats,
    LedgerBackupManager,
)
from jarvis.kernel.event_log import (
    Event,
    EventIntegrityError,
    EventLog,
)


@pytest.fixture
def populated_log(tmp_path: Path) -> EventLog:
    db_file = tmp_path / "test_log.db"
    log = EventLog(db_path=db_file)
    for i in range(5):
        log.append(
            Event(
                stream_id="mission.test",
                event_type="test.step",
                principal_id="tester",
                payload={"step_index": i, "data": f"content_{i}"},
            )
        )
    return log


def test_create_online_backup(tmp_path: Path, populated_log: EventLog):
    backup_dir = tmp_path / "backups"
    manager = LedgerBackupManager(
        event_log=populated_log,
        backup_dir=backup_dir,
    )

    manifest = manager.create_backup(label="test-snapshot")
    assert isinstance(manifest, BackupManifest)
    assert manifest.event_count == 5
    assert manifest.last_seq == 5
    assert manifest.label == "test-snapshot"
    assert manifest.wal_checkpointed is True

    # Verify files created on disk
    assert Path(manifest.backup_file_path).exists()
    assert Path(manifest.manifest_file_path).exists()

    # Loaded manifest matches
    loaded = manager.load_manifest(manifest.backup_id)
    assert loaded.backup_id == manifest.backup_id
    assert loaded.projection_digest == manifest.projection_digest
    assert loaded.db_sha256 == manifest.db_sha256


def test_wal_checkpoint(tmp_path: Path, populated_log: EventLog):
    manager = LedgerBackupManager(event_log=populated_log)
    stats = manager.checkpoint_wal()
    assert isinstance(stats, CheckpointStats)
    assert stats.busy == 0


def test_verify_backup_integrity(tmp_path: Path, populated_log: EventLog):
    backup_dir = tmp_path / "backups"
    manager = LedgerBackupManager(
        event_log=populated_log,
        backup_dir=backup_dir,
    )

    manifest = manager.create_backup()
    # Verification succeeds
    assert manager.verify_backup(manifest.backup_id) is True

    # Tamper with backup file
    backup_path = Path(manifest.backup_file_path)
    with open(backup_path, "r+b") as f:
        f.seek(100)
        original_byte = f.read(1)
        f.seek(100)
        f.write(b"\xff" if original_byte != b"\xff" else b"\x00")

    # Verification must fail with integrity error
    with pytest.raises(EventIntegrityError):
        manager.verify_backup(manifest.backup_id)


def test_disaster_recovery_restore(tmp_path: Path, populated_log: EventLog):
    backup_dir = tmp_path / "backups"
    manager = LedgerBackupManager(
        event_log=populated_log,
        backup_dir=backup_dir,
    )

    original_digest = populated_log.projection_digest()
    manifest = manager.create_backup(label="dr-base")

    # Catastrophic failure simulation: destroy the active database
    populated_log.close()
    active_db = Path(populated_log.db_path)
    active_db.unlink()

    # Restore disaster recovery backup to fresh location
    restored_db_path = tmp_path / "restored.db"
    restored_log = manager.restore_backup(
        backup_id_or_path=manifest.backup_id,
        target_db_path=restored_db_path,
    )

    try:
        events = restored_log.replay()
        assert len(events) == 5
        assert restored_log.projection_digest() == original_digest
        assert restored_log.projection_digest() == manifest.projection_digest
    finally:
        restored_log.close()


def test_restore_overwrite_protection(tmp_path: Path, populated_log: EventLog):
    backup_dir = tmp_path / "backups"
    manager = LedgerBackupManager(
        event_log=populated_log,
        backup_dir=backup_dir,
    )

    manifest = manager.create_backup()
    existing_target = tmp_path / "existing.db"
    existing_target.write_text("existing data")

    # Overwrite=False must fail-closed
    with pytest.raises(FileExistsError):
        manager.restore_backup(
            backup_id_or_path=manifest.backup_id,
            target_db_path=existing_target,
            overwrite=False,
        )


def test_backup_rotation_policy(tmp_path: Path, populated_log: EventLog):
    backup_dir = tmp_path / "backups"
    manager = LedgerBackupManager(
        event_log=populated_log,
        backup_dir=backup_dir,
        max_retained_backups=2,
    )

    b1 = manager.create_backup(label="b1")
    b2 = manager.create_backup(label="b2")
    b3 = manager.create_backup(label="b3")

    remaining = manager.list_backups()
    assert len(remaining) == 2
    remaining_ids = [m.backup_id for m in remaining]
    assert b1.backup_id not in remaining_ids
    assert b2.backup_id in remaining_ids
    assert b3.backup_id in remaining_ids

    # Check files pruned on disk
    assert not Path(b1.backup_file_path).exists()
    assert not Path(b1.manifest_file_path).exists()


def test_backup_emits_events_to_live_log(tmp_path: Path, populated_log: EventLog):
    backup_dir = tmp_path / "backups"
    manager = LedgerBackupManager(
        event_log=populated_log,
        backup_dir=backup_dir,
    )

    manifest = manager.create_backup()
    manager.verify_backup(manifest.backup_id)

    # Check that events were appended to the live ledger
    events = populated_log.replay()
    event_types = [e.event_type for e in events]
    assert "system.backup.created" in event_types
    assert "system.backup.verified" in event_types
