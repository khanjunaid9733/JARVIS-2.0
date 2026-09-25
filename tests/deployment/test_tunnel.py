from __future__ import annotations

import pytest
from cryptography.exceptions import InvalidTag

from jarvis.deployment.tunnel import (
    AuthenticationFailedError,
    ReplayAttackError,
    SecureTunnelEndpoint,
    TunnelSecurityError,
    TunnelState,
)


def test_tunnel_mutual_handshake_success():
    client = SecureTunnelEndpoint(node_id="phone_client")
    server = SecureTunnelEndpoint(node_id="workstation_hub")

    # Client initiates Hello
    hello = client.create_hello()
    assert client.state == TunnelState.CONNECTING

    # Server receives Hello, returns Welcome
    welcome = server.handle_hello_and_welcome(hello)
    assert server.state == TunnelState.AUTHENTICATED
    assert server.peer_node_id == "phone_client"

    # Client receives Welcome, establishes session
    client.complete_client_handshake(welcome)
    assert client.state == TunnelState.AUTHENTICATED
    assert client.peer_node_id == "workstation_hub"


def test_tunnel_encrypt_and_decrypt_roundtrip():
    client = SecureTunnelEndpoint(node_id="phone")
    server = SecureTunnelEndpoint(node_id="server")

    hello = client.create_hello()
    welcome = server.handle_hello_and_welcome(hello)
    client.complete_client_handshake(welcome)

    # Client sends secret telemetry to server
    message = b"GPS: 37.7749,-122.4194|Battery: 92%"
    packet = client.encrypt_packet(message)

    # Server decrypts packet
    decrypted = server.decrypt_packet(packet)
    assert decrypted == message


def test_tunnel_rejects_unauthorized_client_key():
    server = SecureTunnelEndpoint(
        node_id="server",
        allowed_peer_keys={"phone": "00" * 32},  # bogus expected key
    )
    client = SecureTunnelEndpoint(node_id="phone")

    hello = client.create_hello()
    with pytest.raises(AuthenticationFailedError) as exc:
        server.handle_hello_and_welcome(hello)
    assert "does not match authorized key" in str(exc.value)


def test_tunnel_rejects_tampered_handshake_signature():
    client = SecureTunnelEndpoint(node_id="phone")
    server = SecureTunnelEndpoint(node_id="server")

    hello = client.create_hello()
    # Corrupt one byte of client signature
    tampered_sig = bytearray(hello.signature)
    tampered_sig[0] ^= 0xFF
    tampered_hello = hello.__class__(
        client_node_id=hello.client_node_id,
        client_public_key_hex=hello.client_public_key_hex,
        client_nonce=hello.client_nonce,
        timestamp_utc=hello.timestamp_utc,
        signature=bytes(tampered_sig),
    )

    with pytest.raises(AuthenticationFailedError):
        server.handle_hello_and_welcome(tampered_hello)


def test_tunnel_anti_replay_rejects_duplicate_packet():
    client = SecureTunnelEndpoint(node_id="phone")
    server = SecureTunnelEndpoint(node_id="server")

    hello = client.create_hello()
    welcome = server.handle_hello_and_welcome(hello)
    client.complete_client_handshake(welcome)

    packet = client.encrypt_packet(b"Transfer $500")
    first_decrypted = server.decrypt_packet(packet)
    assert first_decrypted == b"Transfer $500"

    # Replay attack: send the exact same packet again
    with pytest.raises(ReplayAttackError) as exc:
        server.decrypt_packet(packet)
    assert "Replay attack detected" in str(exc.value)


def test_tunnel_ciphertext_tampering_raises_integrity_error():
    client = SecureTunnelEndpoint(node_id="phone")
    server = SecureTunnelEndpoint(node_id="server")

    hello = client.create_hello()
    welcome = server.handle_hello_and_welcome(hello)
    client.complete_client_handshake(welcome)

    packet = bytearray(client.encrypt_packet(b"Sensitive Mission Intent"))
    # Corrupt ciphertext byte
    packet[-1] ^= 0xFF

    with pytest.raises(InvalidTag):
        server.decrypt_packet(bytes(packet))


def test_unauthenticated_operation_raises():
    endpoint = SecureTunnelEndpoint(node_id="standalone")
    assert endpoint.state == TunnelState.DISCONNECTED

    with pytest.raises(TunnelSecurityError) as exc:
        endpoint.encrypt_packet(b"test")
    assert "not authenticated" in str(exc.value)

    with pytest.raises(TunnelSecurityError) as exc:
        endpoint.decrypt_packet(b"0" * 32)
    assert "not authenticated" in str(exc.value)
