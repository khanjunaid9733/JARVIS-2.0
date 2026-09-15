from __future__ import annotations

import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class AuthorityUnavailableError(RuntimeError):
    """Typed `authority.unavailable` failure. ADR-007: missing creator key is
    fail-closed — authority operations are rejected, never bypassed."""


class CreatorIdentity:
    """The Creator keypair — trust anchor of the capability registry (ADR-003,
    ADR-007).

    - Algorithm: Ed25519 (`cryptography`).
    - Storage: `~/.jarvis/keys/creator.ed25519` (raw 32-byte seed), mode 0600.
    - Fingerprint: first 8 hex of SHA-256(public key). Emitted as the pairing
      code in the §127.1 smoke test.
    - Signing scope (M1): authority events (`capability.provider_added` /
      `provider_promoted` / `provider_deprecated` / `provider_revoked`) and
      creator approvals; detached signature stored on the event.
    - Missing key: fail closed (`AuthorityUnavailableError`).
    """

    DEFAULT_HOME = "~/.jarvis"
    RELATIVE_KEY_PATH = Path("keys") / "creator.ed25519"
    PACKING_FINGERPRINT_LEN = 8  # first 8 hex of SHA-256(pubkey)

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
        """Generate a new keypair and write it to keys_dir (0600). No passphrase
        in development — an accepted M1 risk, recorded in ADR-007."""
        key_path = cls._resolve_key_path(keys_dir)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        private_key = Ed25519PrivateKey.generate()
        seed = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, seed)
        finally:
            os.close(fd)
        # Best-effort 0600. On POSIX this is authoritative; on Windows the mode
        # maps to the read-only bit only (see ADR-008 portability note).
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
        return cls(private_key, source_path=key_path)

    @classmethod
    def load(cls, keys_dir: Path | str | None = None) -> "CreatorIdentity":
        """Load the creator keypair from disk. Missing/corrupt key -> fail closed."""
        key_path = cls._resolve_key_path(keys_dir)
        if not key_path.exists():
            raise AuthorityUnavailableError(
                f"creator key not found at {key_path}. Run load_or_create? "
                "Authority operations cannot proceed without it (ADR-007 fail-closed)."
            )
        try:
            seed = key_path.read_bytes()
            private_key = Ed25519PrivateKey.from_private_bytes(seed)
        except (OSError, ValueError, TypeError) as exc:
            raise AuthorityUnavailableError(
                f"creator key at {key_path} is corrupt or unreadable: {exc}"
            ) from exc
        return cls(private_key, source_path=key_path)

    @classmethod
    def load_or_create(
        cls, keys_dir: Path | str | None = None
    ) -> "CreatorIdentity":
        """Load if present, otherwise create. For bootstrap paths such as
        `jarvis init` that are allowed to establish the Creator identity."""
        key_path = cls._resolve_key_path(keys_dir)
        if key_path.exists():
            try:
                return cls.load(keys_dir)
            except AuthorityUnavailableError:
                return cls.create(keys_dir)
        return cls.create(keys_dir)

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

    @property
    def fingerprint(self) -> str:
        """First 8 hex chars of SHA-256(public key) — the pairing code."""
        return hashlib.sha256(self.public_key_bytes).hexdigest()[
            : self.PACKING_FINGERPRINT_LEN
        ]

    def public_key_object(self) -> Ed25519PublicKey:
        return self._private_key.public_key()

    # ---- signing / verification -------------------------------------------

    def sign_detached(self, data: bytes) -> bytes:
        """Detached Ed25519 signature, stored on the authority event."""
        return self._private_key.sign(data)

    @staticmethod
    def verify_detached(
        public_key_bytes: bytes,
        data: bytes,
        signature: bytes,
    ) -> bool:
        """Return True if the signature is valid for data under the key."""
        try:
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature, data)
            return True
        except Exception:
            return False

    def export_signable(self, *, event_id: str, event_sha256: str) -> bytes:
        """Canonical byte string that the creator signs for an authority event.
        Detached signature + fingerprint are recorded on the event."""
        from .event_log import _canonical_json

        return _canonical_json(
            {"sac": "jarvis-authority-v1", "event_id": event_id, "event_sha256": event_sha256}
        )

    # ---- helpers ----------------------------------------------------------

    @classmethod
    def _resolve_key_path(cls, keys_dir: Path | str | None = None) -> Path:
        if keys_dir is not None:
            return Path(keys_dir).expanduser() / cls.RELATIVE_KEY_PATH.name
        home = os.environ.get("JARVIS_HOME") or cls.DEFAULT_HOME
        return Path(home).expanduser() / cls.RELATIVE_KEY_PATH