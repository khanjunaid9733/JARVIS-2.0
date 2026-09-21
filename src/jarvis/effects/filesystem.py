from __future__ import annotations

"""Hermetic Filesystem Effect & Sandbox Adapter (Milestone M2.6, spec §83 / §105.1).

Provides sandboxed, path-jailed filesystem operations behind the
`EffectEnvelopeEngine` (`ProviderAdapter` protocol) with atomic write
guarantees and byte-identical rollback capability.

Invariants:
1. Path Jail Enforcement: Every target path is resolved against the configured
   jail root (workspace directory). Any attempt to escape the jail boundary
   (via `..`, absolute external paths, or symlinks) raises `PathJailError`
   and refuses execution before any filesystem mutation occurs.
2. Atomic Writes: Mutations are written to a sibling temporary file and
   atomically replaced via `os.replace`. Partial or interrupted writes cannot
   corrupt the target destination.
3. Byte-Identical Rollback: Prior file states are snapshotted before mutation.
   Invoking rollback restores the exact prior bytes, or removes newly created
   files cleanly.
4. ProviderAdapter Protocol Compliance: Satisfies `jarvis.kernel.registry.ProviderAdapter`
   for the seeded `fs.default` provider exposing `fs.read` and `fs.write`.
5. Strictly Additive: Resides in `src/jarvis/effects/` without modifying frozen
   kernel modules.
"""

import hashlib
import os
from pathlib import Path
from typing import Any, Mapping
import uuid

from pydantic import BaseModel, ConfigDict, Field


class PathJailError(PermissionError):
    """Raised when a requested path escapes the configured sandbox jail root."""


class BackupRecord(BaseModel):
    """Snapshot of a file's state prior to mutation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    backup_id: str
    target_path: str
    existed: bool
    prior_bytes: bytes
    prior_sha256: str


class FilesystemSandbox:
    """Enforces workspace path jailing and manages atomic backups and rollbacks."""

    def __init__(self, jail_root: str | Path) -> None:
        self._jail_root = Path(jail_root).resolve()
        self._backups: dict[str, BackupRecord] = {}

    @property
    def jail_root(self) -> Path:
        return self._jail_root

    def resolve_jailed(self, requested_path: str | Path) -> Path:
        """Resolves a path relative to the jail root and enforces containment."""
        raw = Path(requested_path)
        if raw.is_absolute():
            candidate = raw.resolve()
        else:
            candidate = (self._jail_root / raw).resolve()

        try:
            candidate.relative_to(self._jail_root)
        except ValueError as exc:
            raise PathJailError(
                f"Path '{requested_path}' (resolved: '{candidate}') escapes jail root '{self._jail_root}'"
            ) from exc

        return candidate

    def read_file(self, requested_path: str | Path, encoding: str = "utf-8") -> dict[str, Any]:
        """Reads a jailed file and returns content, byte count, and SHA-256."""
        path = self.resolve_jailed(requested_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found in jail: '{requested_path}'")

        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        content = data.decode(encoding, errors="replace")

        return {
            "path": str(path.relative_to(self._jail_root)),
            "content": content,
            "bytes_read": len(data),
            "sha256": digest,
            "ok": True,
        }

    def write_file_atomic(
        self,
        requested_path: str | Path,
        content: str | bytes,
        *,
        encoding: str = "utf-8",
    ) -> dict[str, Any]:
        """Atomically writes content to a jailed file with pre-mutation backup."""
        path = self.resolve_jailed(requested_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = content.encode(encoding) if isinstance(content, str) else content
        digest = hashlib.sha256(payload).hexdigest()

        # Capture pre-mutation state for rollback
        backup_id = f"bak-{uuid.uuid4().hex[:12]}"
        if path.exists():
            prior_data = path.read_bytes()
            prior_digest = hashlib.sha256(prior_data).hexdigest()
            record = BackupRecord(
                backup_id=backup_id,
                target_path=str(path),
                existed=True,
                prior_bytes=prior_data,
                prior_sha256=prior_digest,
            )
        else:
            record = BackupRecord(
                backup_id=backup_id,
                target_path=str(path),
                existed=False,
                prior_bytes=b"",
                prior_sha256="",
            )
        self._backups[backup_id] = record

        # Atomic write via staging file in same directory
        temp_file = path.parent / f".tmp.{path.name}.{uuid.uuid4().hex[:8]}"
        try:
            with open(temp_file, "wb") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temp_file, path)
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

        return {
            "path": str(path.relative_to(self._jail_root)),
            "bytes_written": len(payload),
            "sha256": digest,
            "backup_id": backup_id,
            "prior_sha256": record.prior_sha256 or None,
            "ok": True,
        }

    def rollback(self, backup_id: str) -> bool:
        """Restores a prior file state or deletes a newly created file."""
        record = self._backups.get(backup_id)
        if record is None:
            raise KeyError(f"Unknown backup id: '{backup_id}'")

        target = Path(record.target_path)
        if record.existed:
            target.parent.mkdir(parents=True, exist_ok=True)
            temp_file = target.parent / f".tmp.rollback.{target.name}.{uuid.uuid4().hex[:8]}"
            try:
                with open(temp_file, "wb") as fh:
                    fh.write(record.prior_bytes)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(temp_file, target)
            finally:
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except OSError:
                        pass
        else:
            if target.exists():
                target.unlink()

        return True


class FilesystemEffectAdapter:
    """Adapter bound to `fs.default` provider satisfying ProviderAdapter protocol."""

    def __init__(
        self,
        sandbox: FilesystemSandbox,
        provider_id: str = "fs.default",
    ) -> None:
        self._sandbox = sandbox
        self._provider_id = provider_id

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def sandbox(self) -> FilesystemSandbox:
        return self._sandbox

    async def invoke(
        self,
        contract_id: str,
        version: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Dispatches filesystem contracts under jail constraints."""
        if contract_id == "fs.read":
            path = args.get("path")
            if not path:
                raise ValueError("Argument 'path' is required for fs.read")
            encoding = args.get("encoding", "utf-8")
            return self._sandbox.read_file(path, encoding=encoding)

        if contract_id == "fs.write":
            path = args.get("path")
            if not path:
                raise ValueError("Argument 'path' is required for fs.write")
            content = args.get("content", "")
            encoding = args.get("encoding", "utf-8")
            return self._sandbox.write_file_atomic(path, content, encoding=encoding)

        if contract_id == "fs.rollback":
            backup_id = args.get("backup_id")
            if not backup_id:
                raise ValueError("Argument 'backup_id' is required for fs.rollback")
            restored = self._sandbox.rollback(backup_id)
            return {"backup_id": backup_id, "restored": restored, "ok": True}

        raise ValueError(f"Unsupported contract '{contract_id}' for provider '{self._provider_id}'")

    def health_check(self) -> bool:
        """Verifies the sandbox jail root is an accessible directory."""
        return self._sandbox.jail_root.is_dir()


__all__ = [
    "BackupRecord",
    "FilesystemEffectAdapter",
    "FilesystemSandbox",
    "PathJailError",
]
