import hashlib
import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from jarvis.kernel.creator import AuthorityUnavailable, CreatorIdentity


@pytest.fixture
def keys_dir(tmp_path):
    return tmp_path / "jarvis_keys"


def test_create_writes_keypair_to_expected_path(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    assert identity.source_path == keys_dir / "creator.ed25519"
    assert identity.source_path.exists()


def test_fingerprint_is_8_lowercase_hex_stable_across_load(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    fp = identity.fingerprint()
    assert len(fp) == 8
    assert fp == fp.lower()
    assert all(c in "0123456789abcdef" for c in fp)
    loaded = CreatorIdentity.load(keys_dir)
    assert loaded.fingerprint() == fp


def test_fingerprint_is_first_8_hex_of_sha256_pubkey(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    expect = hashlib.sha256(identity.public_key_bytes).hexdigest()[:8]
    assert identity.fingerprint() == expect


def test_sign_verify_roundtrip(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    data = b"capability.provider_added|payload"
    sig = identity.sign(data)
    assert identity.verify(data, sig) is True


def test_verify_fails_on_tampered_data(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    data = b"authorize provider x"
    sig = identity.sign(data)
    assert identity.verify(data + b"!", sig) is False


def test_verify_fails_on_different_public_key(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    other = CreatorIdentity.create(keys_dir / "other")
    data = b"authority event"
    sig = identity.sign(data)
    assert identity.verify_with(other.public_key_bytes, data, sig) is False


def test_verify_with_static_path(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    data = b"some authority payload"
    sig = identity.sign(data)
    assert CreatorIdentity.verify_with(identity.public_key_bytes, data, sig) is True


def test_load_missing_file_raises_authority_unavailable(keys_dir):
    with pytest.raises(AuthorityUnavailable):
        CreatorIdentity.load(keys_dir)


def test_load_corrupt_file_raises_authority_unavailable(keys_dir):
    key_path = keys_dir / "creator.ed25519"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(b"\x00" * 31)  # not a valid 32-byte seed
    with pytest.raises(AuthorityUnavailable):
        CreatorIdentity.load(keys_dir)


def test_create_on_existing_key_does_not_overwrite(keys_dir):
    first = CreatorIdentity.create(keys_dir)
    fp_before = first.fingerprint()
    second = CreatorIdentity.create(keys_dir)
    assert second.fingerprint() == fp_before
    assert first.public_key_bytes == second.public_key_bytes


def test_jarvishome_env_override(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("JARVIS_HOME", str(home))
    identity = CreatorIdentity.create()
    assert identity.source_path == home / "keys" / "creator.ed25519"
    assert identity.source_path.exists()
    loaded = CreatorIdentity.load()
    assert loaded.fingerprint() == identity.fingerprint()


def test_load_rejects_empty_key_file(keys_dir):
    key_path = keys_dir / "creator.ed25519"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(b"")
    with pytest.raises(AuthorityUnavailable):
        CreatorIdentity.load(keys_dir)


def test_public_key_serializes_to_raw_for_registry(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    raw = identity.public_key_object().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    assert raw == identity.public_key_bytes
    assert len(raw) == 32


def test_export_signable_is_deterministic_and_signable(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    a = identity.export_signable(event_id="X", event_sha256="Y")
    b = identity.export_signable(event_id="X", event_sha256="Y")
    assert a == b
    assert b"jarvis-authority-v1" in a
    sig = identity.sign(a)
    assert identity.verify(a, sig) is True