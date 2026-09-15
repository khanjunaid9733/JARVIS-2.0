from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import sys
from pathlib import Path

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

logger = logging.getLogger(__name__)

# Creator identity lives at kernel/creator.py, a sibling of event_log.py.
# Signature storage (M1 decision, ADR-007 ambiguity #1): detached signatures
# for authority events are stored in the event's payload_json (option a).
# ADR-005's schema is NOT amended in M1.


class AuthorityUnavailable(RuntimeError):
    """Typed fail-closed failure. Raised whenever the creator key cannot be
    loaded, read, or used for signing. Never bypassed; never falls back to an
    ephemeral key."""


class CreatorIdentity:
    """The Creator keypair — root trust anchor of the capability registry
    (ADR-003, ADR-007, spec §105).

    - Ed25519 via `cryptography`.
    - Storage: <JARVIS_HOME>/keys/creator.ed25519 (raw 32-byte seed).
      JARVIS_HOME defaults to ~/.jarvis. No passphrase in M1 (accepted risk,
      ADR-007).
    - fingerprint(): first 8 lowercase hex chars of SHA-256(public key).
    - Fail closed: any missing/unreadable/corrupt key raises AuthorityUnavailable.
    """

    DEFAULT_HOME = "~/.jarvis"
    RELATIVE_KEY_PATH = Path("keys") / "creator.ed25519"
    FINGERPRINT_LEN = 8

    def __init__(
        self,
        private_key: Ed25519PrivateKey,
        source_path: Path | None = None,
    ) -> None:
        self._private_key = private_key
        self._source_path = source_path

    # ---- construction -----------------------------------------------------

    @classmethod
    def create(cls, keys_dir: Path | str | None = None) -> "CreatorIdentity":
        """Idempotent: returns the existing identity if one is on disk,
        otherwise generates and persists a new one. Never overwrites.
        If the key file exists but is corrupt, create() raises
        AuthorityUnavailable rather than silently regenerating over
        existing material (fail-closed invariant)."""
        key_path = cls._resolve_key_path(keys_dir)
        if key_path.exists():
            return cls.load(keys_dir)
        return cls._generate(key_path)

    @classmethod
    def load(cls, keys_dir: Path | str | None = None) -> "CreatorIdentity":
        """Load from disk. Raises AuthorityUnavailable if the key file is
        missing, unreadable, or corrupt. Fail closed."""
        key_path = cls._resolve_key_path(keys_dir)
        if not key_path.exists():
            raise AuthorityUnavailable(
                f"creator key not found at {key_path}"
            )
        try:
            seed = key_path.read_bytes()
            private_key = Ed25519PrivateKey.from_private_bytes(seed)
        except (OSError, ValueError, TypeError, UnsupportedAlgorithm) as exc:
            raise AuthorityUnavailable(
                f"creator key at {key_path} is unreadable or corrupt: {exc}"
            ) from exc
        return cls(private_key, source_path=key_path)

    @classmethod
    def _generate(cls, key_path: Path) -> "CreatorIdentity":
        key_path.parent.mkdir(parents=True, exist_ok=True)
        private_key = Ed25519PrivateKey.generate()
        seed = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        # O_BINARY: on Windows os.open defaults to text mode, which would
        # mangle the seed (LF -> CRLF). POSIX has no O_BINARY (0 ok).
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0)
        fd = os.open(key_path, flags, 0o600)
        try:
            os.write(fd, seed)
        finally:
            os.close(fd)
        cls._restrict_permissions(key_path)
        return cls(private_key, source_path=key_path)

    @staticmethod
    def _restrict_permissions(key_path: Path) -> None:
        """Best-effort 0600 (documented decision for ADR-007 ambiguity #2):

        - os.chmod first: authoritative on POSIX, maps to the read-only bit
          on Windows.
        - On Windows, additionally run icacls to strip inherited ACLs and
          grant only the current user read access.
        - Inability to restrict is logged, not fatal (fail-closed still holds
          at the load boundary, which is the security gate).
        """
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            logger.warning("os.chmod(0600) failed for %s", key_path)
        if sys.platform != "win32":
            return
        username = os.environ.get("USERNAME") or os.environ.get("USER")
        if not username:
            logger.warning("cannot restrict ACLs: no USERNAME. Key: %s", key_path)
            return
        try:
            result = subprocess.run(
                [
                    "icacls",
                    str(key_path),
                    "/inheritance:r",
                    "/grant:r",
                    f"{username}:R",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning(
                    "icacls failed for %s: %s", key_path, result.stderr.strip()
                )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("icacls unavailable for %s: %s", key_path, exc)

    # ---- key material -----------------------------------------------------

    @property
    def source_path(self) -> Path | None:
        return self._source_path

    @property
    def public_key_bytes(self) -> bytes:
        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @property
    def public_key_hex(self) -> str:
        return self.public_key_bytes.hex()

    def fingerprint(self) -> str:
        """First 8 lowercase hex chars of SHA-256(public key)."""
        return hashlib.sha256(self.public_key_bytes).hexdigest()[
            : self.FINGERPRINT_LEN
        ]

    def public_key_object(self) -> Ed25519PublicKey:
        return self._private_key.public_key()

    # ---- signing -----------------------------------------------------------

    def sign(self, data: bytes) -> bytes:
        """Detached Ed25519 signature. Raises AuthorityUnavailable on failure."""
        try:
            return self._private_key.sign(data)
        except Exception as exc:
            raise AuthorityUnavailable(f"signing failed: {exc}") from exc

    def verify(self, data: bytes, signature: bytes) -> bool:
        """Verify against the creator's own public key."""
        return self.verify_with(self.public_key_bytes, data, signature)

    @staticmethod
    def verify_with(
        public_key_bytes: bytes, data: bytes, signature: bytes
    ) -> bool:
        """Verify a creator signature with an explicit public key, so other
        principals need no access to the private key."""
        try:
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature, data)
            return True
        except Exception:
            return False

    def export_signable(self, *, event_id: str, event_sha256: str) -> bytes:
        """Canonical byte string the creator signs for an authority event.
        The detached signature is stored in the event's payload_json (M1
        decision, ambiguity #1)."""
        from .event_log import _canonical_json

        return _canonical_json(
            {
                "sac": "jarvis-authority-v1",
                "event_id": event_id,
                "event_sha256": event_sha256,
            }
        )

    # ---- paths -------------------------------------------------------------

    @classmethod
    def _resolve_key_path(cls, keys_dir: Path | str | None = None) -> Path:
        if keys_dir is not None:
            return Path(keys_dir).expanduser() / cls.RELATIVE_KEY_PATH.name
        home = os.environ.get("JARVIS_HOME") or cls.DEFAULT_HOME
        return Path(home).expanduser() / cls.RELATIVE_KEY_PATH