import hashlib
import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from jarvis.kernel.creator_identity import (
    AuthorityUnavailableError,
    CreatorIdentity,
)


@pytest.fixture
def keys_dir(tmp_path):
    return tmp_path / "jarvis_keys"


def test_create_persists_0600_key_file(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    key_path = keys_dir / "creator.ed25519"
    assert key_path.exists()
    mode = os.stat(key_path).st_mode & 0o777
    if os.name == "posix":
        # POSIX enforces 0600 exactly.
        assert mode == 0o600
    else:
        # Windows st_mode is not a real ACL (os.chmod maps only to the
        # read-only bit). ADR-007/008 record this portability limit.
        assert key_path.is_file()
    assert identity.source_path == key_path


def test_created_key_loads_with_same_fingerprint(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    loaded = CreatorIdentity.load(keys_dir)
    assert loaded.fingerprint == identity.fingerprint
    assert loaded.public_key_hex == identity.public_key_hex


def test_fingerprint_is_first_8_hex_of_sha256_pubkey(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    expect = hashlib.sha256(identity.public_key_bytes).hexdigest()[:8]
    assert len(identity.fingerprint) == 8
    assert identity.fingerprint == expect


def test_public_key_hex_roundtrip_to_raw_bytes(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    recovered = Ed25519PublicKey.from_public_bytes(bytes.fromhex(identity.public_key_hex))
    assert recovered == identity.public_key_object()


def test_missing_key_fails_closed(keys_dir):
    with pytest.raises(AuthorityUnavailableError):
        CreatorIdentity.load(keys_dir)


def test_corrupt_key_fails_closed(keys_dir):
    key_path = keys_dir / "creator.ed25519"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(b"\x00" * 32 + b"junk")
    with pytest.raises(AuthorityUnavailableError):
        CreatorIdentity.load(keys_dir)


def test_sign_verify_detached_roundtrip(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    data = b"capability.provider_added|payload-bytes"
    sig = identity.sign_detached(data)
    assert CreatorIdentity.verify_detached(identity.public_key_bytes, data, sig) is True


def test_verify_rejects_tampered_data(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    data = b"authorize provider x"
    sig = identity.sign_detached(data)
    assert CreatorIdentity.verify_detached(identity.public_key_bytes, data + b"x", sig) is False


def test_verify_rejects_wrong_key(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    other = CreatorIdentity.create(keys_dir / "other")
    data = b"some authority event"
    sig = identity.sign_detached(data)
    assert CreatorIdentity.verify_detached(other.public_key_bytes, data, sig) is False


def test_export_signable_is_canonical_and_signed(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    signable = identity.export_signable(event_id="01M2HP9EMTK9J4S14DEAC4V3YE", event_sha256="abc123")
    assert b"jarvis-authority-v1" in signable
    assert b'"event_id":"01M2HP9EMTK9J4S14DEAC4V3YE"' in signable
    sig = identity.sign_detached(signable)
    assert CreatorIdentity.verify_detached(identity.public_key_bytes, signable, sig) is True


def test_export_signable_is_deterministic(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    a = identity.export_signable(event_id="X", event_sha256="Y")
    b = identity.export_signable(event_id="X", event_sha256="Y")
    assert a == b


def test_jarvishome_env_override(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("JARVIS_HOME", str(home))
    identity = CreatorIdentity.load_or_create()
    assert identity.source_path == home / "keys" / "creator.ed25519"
    assert identity.source_path.exists()


def test_load_or_create_existing_does_not_recreate(keys_dir):
    first = CreatorIdentity.load_or_create(keys_dir)
    second = CreatorIdentity.load_or_create(keys_dir)
    assert second.fingerprint == first.fingerprint


def test_public_key_serializes_to_raw_for_export(keys_dir):
    identity = CreatorIdentity.create(keys_dir)
    raw = identity.public_key_object().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    assert raw == identity.public_key_bytes
    assert len(raw) == 32