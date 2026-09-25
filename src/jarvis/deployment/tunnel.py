from __future__ import annotations

"""Secure Remote Access & Encrypted Tunnel Seam (src/jarvis/deployment/tunnel.py).

Provides:
1. Mutual cryptographic handshake with Ed25519 signing and verification.
2. Replay-attack protection via monotonic sequence numbers and nonces.
3. Authenticated symmetric encryption (AES-256-GCM) for tunnel payload transport.
4. Transport-agnostic endpoints for companion phone and remote workstation access.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import enum
import os
import struct
import time
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class TunnelState(str, enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATED = "authenticated"
    TERMINATED = "terminated"


class TunnelSecurityError(RuntimeError):
    """Base error for tunnel security failures."""


class AuthenticationFailedError(TunnelSecurityError):
    """Raised when mutual cryptographic handshake verification fails."""


class ReplayAttackError(TunnelSecurityError):
    """Raised when a packet sequence number violates monotonic ordering."""


DOMAIN_HANDSHAKE_TAG = b"jarvis-tunnel-handshake-v1"


@dataclass(frozen=True)
class HandshakeHello:
    client_node_id: str
    client_public_key_hex: str
    client_nonce: bytes
    timestamp_utc: str
    signature: bytes


@dataclass(frozen=True)
class HandshakeWelcome:
    server_node_id: str
    server_public_key_hex: str
    server_nonce: bytes
    timestamp_utc: str
    signature: bytes


class SecureTunnelEndpoint:
    """Cryptographic tunnel endpoint enforcing mutual auth, AES-GCM, and anti-replay."""

    def __init__(
        self,
        node_id: str,
        signing_key: Ed25519PrivateKey | None = None,
        allowed_peer_keys: Mapping[str, str] | None = None,  # node_id -> hex public key
    ) -> None:
        self.node_id = node_id
        self._signing_key = signing_key or Ed25519PrivateKey.generate()
        self.public_key = self._signing_key.public_key()
        self.public_key_hex = self.public_key.public_bytes_raw().hex()
        self.allowed_peer_keys = dict(allowed_peer_keys or {})

        self.state: TunnelState = TunnelState.DISCONNECTED
        self.peer_node_id: str = ""
        self.peer_public_key_hex: str = ""
        self._shared_aesgcm: AESGCM | None = None
        self._local_seq: int = 0
        self._remote_seq: int = 0
        self._local_nonce: bytes = b""

    def create_hello(self) -> HandshakeHello:
        """Client initiates handshake hello packet."""
        self._local_nonce = os.urandom(32)
        now_iso = datetime.now(timezone.utc).isoformat()
        to_sign = DOMAIN_HANDSHAKE_TAG + self.node_id.encode() + self._local_nonce + now_iso.encode()
        sig = self._signing_key.sign(to_sign)

        self.state = TunnelState.CONNECTING
        return HandshakeHello(
            client_node_id=self.node_id,
            client_public_key_hex=self.public_key_hex,
            client_nonce=self._local_nonce,
            timestamp_utc=now_iso,
            signature=sig,
        )

    def handle_hello_and_welcome(self, hello: HandshakeHello) -> HandshakeWelcome:
        """Server receives hello, verifies client, and returns welcome response."""
        # 1. Authorize peer
        if self.allowed_peer_keys and hello.client_node_id in self.allowed_peer_keys:
            expected_key = self.allowed_peer_keys[hello.client_node_id]
            if expected_key != hello.client_public_key_hex:
                raise AuthenticationFailedError("Client public key does not match authorized key.")

        # 2. Verify client signature
        client_pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(hello.client_public_key_hex))
        to_verify = DOMAIN_HANDSHAKE_TAG + hello.client_node_id.encode() + hello.client_nonce + hello.timestamp_utc.encode()
        try:
            client_pub.verify(hello.signature, to_verify)
        except InvalidSignature as e:
            raise AuthenticationFailedError("Client handshake signature verification failed.") from e

        self.peer_node_id = hello.client_node_id
        self.peer_public_key_hex = hello.client_public_key_hex

        # 3. Create server welcome
        server_nonce = os.urandom(32)
        now_iso = datetime.now(timezone.utc).isoformat()
        to_sign = DOMAIN_HANDSHAKE_TAG + self.node_id.encode() + server_nonce + now_iso.encode()
        sig = self._signing_key.sign(to_sign)

        # 4. Derive symmetric session key via combined nonces & key material
        combined_entropy = hello.client_nonce + server_nonce + bytes.fromhex(self.public_key_hex) + bytes.fromhex(hello.client_public_key_hex)
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"jarvis-tunnel-aes-key",
        )
        aes_key = hkdf.derive(combined_entropy)
        self._shared_aesgcm = AESGCM(aes_key)
        self.state = TunnelState.AUTHENTICATED
        self._local_seq = 0
        self._remote_seq = 0

        return HandshakeWelcome(
            server_node_id=self.node_id,
            server_public_key_hex=self.public_key_hex,
            server_nonce=server_nonce,
            timestamp_utc=now_iso,
            signature=sig,
        )

    def complete_client_handshake(self, welcome: HandshakeWelcome) -> None:
        """Client processes server welcome and establishes session key."""
        # 1. Authorize server key if whitelist present
        if self.allowed_peer_keys and welcome.server_node_id in self.allowed_peer_keys:
            expected_key = self.allowed_peer_keys[welcome.server_node_id]
            if expected_key != welcome.server_public_key_hex:
                raise AuthenticationFailedError("Server public key does not match authorized key.")

        # 2. Verify signature
        server_pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(welcome.server_public_key_hex))
        to_verify = DOMAIN_HANDSHAKE_TAG + welcome.server_node_id.encode() + welcome.server_nonce + welcome.timestamp_utc.encode()
        try:
            server_pub.verify(welcome.signature, to_verify)
        except InvalidSignature as e:
            raise AuthenticationFailedError("Server handshake signature verification failed.") from e

        self.peer_node_id = welcome.server_node_id
        self.peer_public_key_hex = welcome.server_public_key_hex

        # 3. Derive symmetric key
        combined_entropy = self._local_nonce + welcome.server_nonce + bytes.fromhex(welcome.server_public_key_hex) + bytes.fromhex(self.public_key_hex)
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"jarvis-tunnel-aes-key",
        )
        aes_key = hkdf.derive(combined_entropy)
        self._shared_aesgcm = AESGCM(aes_key)
        self.state = TunnelState.AUTHENTICATED
        self._local_seq = 0
        self._remote_seq = 0

    def encrypt_packet(self, plaintext: bytes) -> bytes:
        """Encrypts a payload with a unique 12-byte IV and monotonic sequence number."""
        if self.state != TunnelState.AUTHENTICATED or self._shared_aesgcm is None:
            raise TunnelSecurityError("Cannot encrypt: tunnel is not authenticated.")

        self._local_seq += 1
        seq = self._local_seq
        iv = os.urandom(12)
        header = struct.pack(">Q", seq)  # 8 bytes big-endian sequence
        ciphertext = self._shared_aesgcm.encrypt(iv, plaintext, header)

        # Packed format: [8 bytes seq] + [12 bytes IV] + [ciphertext with GCM tag]
        return header + iv + ciphertext

    def decrypt_packet(self, packet: bytes) -> bytes:
        """Decrypts a packet and validates monotonic anti-replay sequence ordering."""
        if self.state != TunnelState.AUTHENTICATED or self._shared_aesgcm is None:
            raise TunnelSecurityError("Cannot decrypt: tunnel is not authenticated.")

        if len(packet) < 20:  # 8 seq + 12 iv
            raise TunnelSecurityError("Packet too short.")

        seq = struct.unpack(">Q", packet[:8])[0]
        iv = packet[8:20]
        ciphertext = packet[20:]
        header = packet[:8]

        # Monotonic sequence check (Anti-Replay)
        if seq <= self._remote_seq:
            raise ReplayAttackError(
                f"Replay attack detected: sequence {seq} <= last seen {self._remote_seq}."
            )

        plaintext = self._shared_aesgcm.decrypt(iv, ciphertext, header)
        self._remote_seq = seq
        return plaintext

    def close(self) -> None:
        self.state = TunnelState.TERMINATED
        self._shared_aesgcm = None
