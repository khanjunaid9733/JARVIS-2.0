from __future__ import annotations

"""Unit & Invariant Tests for Milestone M2.6: Hermetic Filesystem Effect & Sandbox."""

import os
from pathlib import Path
import tempfile

import pytest

from jarvis.effects.filesystem import (
    BackupRecord,
    FilesystemEffectAdapter,
    FilesystemSandbox,
    PathJailError,
)
from jarvis.kernel.effect_envelope import (
    EffectEnvelope,
    EffectEnvelopeEngine,
    EffectFailure,
)
from jarvis.kernel.intent import Budget, Manifest, ResolvedContract
from jarvis.kernel.registry import CapabilityRegistry


@pytest.fixture
def workspace_jail(tmp_path: Path) -> FilesystemSandbox:
    jail_dir = tmp_path / "sandbox_root"
    jail_dir.mkdir(parents=True, exist_ok=True)
    return FilesystemSandbox(jail_dir)


# ---------------------------------------------------------------------------
# 1. Path Jail Enforcement
# ---------------------------------------------------------------------------

def test_path_jail_allows_valid_relative_paths(workspace_jail: FilesystemSandbox):
    resolved = workspace_jail.resolve_jailed("test.txt")
    assert resolved == workspace_jail.jail_root / "test.txt"

    nested = workspace_jail.resolve_jailed("nested/sub/doc.md")
    assert nested == workspace_jail.jail_root / "nested" / "sub" / "doc.md"


def test_path_jail_rejects_parent_traversal(workspace_jail: FilesystemSandbox):
    with pytest.raises(PathJailError) as exc:
        workspace_jail.resolve_jailed("../outside.txt")
    assert "escapes jail root" in str(exc.value)

    with pytest.raises(PathJailError):
        workspace_jail.resolve_jailed("nested/../../outside.txt")


def test_path_jail_rejects_absolute_path_outside_jail(workspace_jail: FilesystemSandbox, tmp_path: Path):
    external = tmp_path / "external_file.txt"
    external.write_text("secret")

    with pytest.raises(PathJailError):
        workspace_jail.resolve_jailed(str(external))


# ---------------------------------------------------------------------------
# 2. Atomic Write & Read
# ---------------------------------------------------------------------------

def test_atomic_write_and_read(workspace_jail: FilesystemSandbox):
    content = "Hello, JARVIS 2.0 Hermetic Filesystem!"
    write_res = workspace_jail.write_file_atomic("data/hello.txt", content)

    assert write_res["ok"] is True
    assert write_res["bytes_written"] == len(content.encode("utf-8"))
    assert write_res["path"] == str(Path("data/hello.txt"))
    assert write_res["prior_sha256"] is None

    read_res = workspace_jail.read_file("data/hello.txt")
    assert read_res["ok"] is True
    assert read_res["content"] == content
    assert read_res["bytes_read"] == len(content.encode("utf-8"))
    assert read_res["sha256"] == write_res["sha256"]


def test_read_missing_file_raises_not_found(workspace_jail: FilesystemSandbox):
    with pytest.raises(FileNotFoundError):
        workspace_jail.read_file("nonexistent.txt")


# ---------------------------------------------------------------------------
# 3. Backup & Byte-Identical Rollback
# ---------------------------------------------------------------------------

def test_rollback_of_new_file_deletes_it(workspace_jail: FilesystemSandbox):
    write_res = workspace_jail.write_file_atomic("new_file.txt", "fresh data")
    backup_id = write_res["backup_id"]
    file_path = workspace_jail.jail_root / "new_file.txt"

    assert file_path.is_file()

    # Rollback removes the file
    workspace_jail.rollback(backup_id)
    assert not file_path.exists()


def test_rollback_of_modified_file_restores_prior_bytes(workspace_jail: FilesystemSandbox):
    original_text = "ORIGINAL_STATE_V1\nLine 2\nLine 3"
    workspace_jail.write_file_atomic("config.cfg", original_text)

    # Modify the file
    new_text = "MUTATED_STATE_V2\nCorrupted content"
    write_res = workspace_jail.write_file_atomic("config.cfg", new_text)
    backup_id = write_res["backup_id"]

    # Verify modification took effect
    read_mod = workspace_jail.read_file("config.cfg")
    assert read_mod["content"] == new_text

    # Rollback restores original state byte-for-byte
    workspace_jail.rollback(backup_id)
    read_restored = workspace_jail.read_file("config.cfg")
    assert read_restored["content"] == original_text
    assert read_restored["bytes_read"] == len(original_text.encode("utf-8"))


# ---------------------------------------------------------------------------
# 4. EffectEnvelopeEngine Integration
# ---------------------------------------------------------------------------

def _make_manifest(contract_id: str, args: dict | None = None) -> Manifest:
    return Manifest(
        manifest_id="manifest-fs-1",
        intent_id="intent-fs-1",
        contracts=[
            ResolvedContract(
                id=contract_id, version="1.0.0", args=dict(args or {})
            )
        ],
        required_capabilities=[contract_id],
        budget=Budget(),
        constraints={},
        risk_class="safe",
        manifest_sha256="0" * 64,
        created_at_utc="2026-09-21T00:00:00Z",
    )


@pytest.mark.anyio
async def test_envelope_engine_fs_write_and_read(workspace_jail: FilesystemSandbox):
    adapter = FilesystemEffectAdapter(workspace_jail)
    engine = EffectEnvelopeEngine(
        CapabilityRegistry.seed_m1_defaults(),
        {"fs.default": adapter},
    )

    # 1. fs.write through envelope
    manifest_write = _make_manifest("fs.write", {"path": "out/test.json"})
    content = '{"status": "verified"}'
    envelope_write = await engine.run(
        manifest_write,
        "fs.write",
        intended_change={"path": "out/test.json", "content": content},
        postconditions={"ok": True},
        idempotency_key="k-fs-write-1",
        capability_args={"path": "out/test.json", "content": content},
    )

    assert isinstance(envelope_write, EffectEnvelope)
    assert envelope_write.verification.passed is True
    assert envelope_write.provider_id == "fs.default"

    # 2. fs.read through envelope
    manifest_read = _make_manifest("fs.read", {"path": "out/test.json"})
    envelope_read = await engine.run(
        manifest_read,
        "fs.read",
        intended_change={"path": "out/test.json"},
        postconditions={"ok": True},
        idempotency_key="k-fs-read-1",
        capability_args={"path": "out/test.json"},
    )

    assert isinstance(envelope_read, EffectEnvelope)
    assert envelope_read.verification.passed is True


@pytest.mark.anyio
async def test_envelope_engine_path_jail_refusal(workspace_jail: FilesystemSandbox):
    adapter = FilesystemEffectAdapter(workspace_jail)
    engine = EffectEnvelopeEngine(
        CapabilityRegistry.seed_m1_defaults(),
        {"fs.default": adapter},
    )

    manifest_escape = _make_manifest("fs.write", {"path": "../../etc/shadow"})
    failure = await engine.run(
        manifest_escape,
        "fs.write",
        intended_change={"path": "../../etc/shadow", "content": "malicious"},
        postconditions={"ok": True},
        idempotency_key="k-fs-escape",
        capability_args={"path": "../../etc/shadow", "content": "malicious"},
    )

    assert isinstance(failure, EffectFailure)
    assert failure.reason == "adapter_error"
    assert "escapes jail root" in failure.detail


# ---------------------------------------------------------------------------
# 5. Health Check
# ---------------------------------------------------------------------------

def test_adapter_health_check(workspace_jail: FilesystemSandbox, tmp_path: Path):
    adapter = FilesystemEffectAdapter(workspace_jail)
    assert adapter.health_check() is True

    dead_sandbox = FilesystemSandbox(tmp_path / "does_not_exist_xyz")
    dead_adapter = FilesystemEffectAdapter(dead_sandbox)
    assert dead_adapter.health_check() is False
