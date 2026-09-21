from __future__ import annotations

"""Unit tests for M2.8 Key-Based Creator Authority (src/jarvis/kernel/crypto_authority.py).

Verifies:
1. Ed25519 signature verification for creator-gated actions (reopen, merge proposal, policy override).
2. Cryptographic capability registry mutations (NAT-02 second half completion).
3. Fail-closed rejection: Tampered signatures, forged keys, invalid hex, and mismatched
   targets/actions strictly raise `AuthorityUnavailable`.
4. Deterministic signable byte generation and domain separation.
"""

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jarvis.kernel.creator import AuthorityUnavailable, CreatorIdentity
from jarvis.kernel.crypto_authority import (
    DOMAIN_TAG,
    AuthorityGrant,
    CreatorActionType,
    CryptoAuthority,
    CryptoCapabilityRegistry,
    create_authority_grant,
)
from jarvis.kernel.registry import (
    CapabilityRegistry,
    ContractDef,
    ProviderBinding,
    ProviderMeta,
)


@pytest.fixture
def creator_keys_dir(tmp_path):
    """Temporary keys directory with a valid CreatorIdentity."""
    path = tmp_path / "creator_keys"
    return path


@pytest.fixture
def creator_identity(creator_keys_dir):
    return CreatorIdentity.create(creator_keys_dir)


@pytest.fixture
def authority(creator_identity):
    return CryptoAuthority(creator_public_key=creator_identity.public_key_bytes)


def _sample_binding(provider_id: str = "test.provider") -> ProviderBinding:
    return ProviderBinding(
        meta=ProviderMeta(
            provider_id=provider_id,
            version="1.0.0",
            license="Apache-2.0",
            license_compatibility="approved",
            adapter="jarvis.adapters.test",
            trust_level="sandboxed",
            process_model="in_process",
            network="none",
            health_check="ping",
            cve_status="checked_clean",
            provenance_added_by="creator",
            provenance_added_at_utc="2026-09-21T00:00:00Z",
            provenance_reason="test registration",
        ),
        contracts=[
            ContractDef(
                contract_id=f"{provider_id}.echo",
                version="1.0.0",
                args_schema={"type": "object", "properties": {"msg": {"type": "string"}}},
            )
        ],
    )


# ---------------------------------------------------------------------------
# Grant Issuance & Signable Payload Invariants
# ---------------------------------------------------------------------------

def test_grant_creation_and_canonical_signable_bytes(creator_identity):
    grant = create_authority_grant(
        creator_identity,
        action=CreatorActionType.REOPEN,
        target="M2.8",
        parameters={"reason": "audit fix"},
        created_at_utc="2026-09-21T12:00:00.000Z",
        nonce="nonce-12345",
    )

    assert grant.action == "reopen"
    assert grant.target == "M2.8"
    assert grant.parameters == {"reason": "audit fix"}
    assert grant.created_at_utc == "2026-09-21T12:00:00.000Z"
    assert grant.nonce == "nonce-12345"
    assert grant.creator_fingerprint == creator_identity.fingerprint()
    assert len(grant.signature_hex) == 128  # 64 bytes in hex
    assert isinstance(grant.signature_bytes, bytes)
    assert len(grant.signature_bytes) == 64

    signable = grant.compute_signable_bytes()
    assert DOMAIN_TAG.encode("utf-8") in signable
    assert b'"action":"reopen"' in signable
    assert b'"target":"M2.8"' in signable


def test_signable_payload_deterministic_across_identical_inputs(creator_identity):
    grant_a = create_authority_grant(
        creator_identity,
        action="policy_override",
        target="privacy.strict",
        parameters={"allowed": True},
        created_at_utc="2026-09-21T00:00:00.000Z",
        nonce="fixed-nonce",
    )
    grant_b = create_authority_grant(
        creator_identity,
        action="policy_override",
        target="privacy.strict",
        parameters={"allowed": True},
        created_at_utc="2026-09-21T00:00:00.000Z",
        nonce="fixed-nonce",
    )
    assert grant_a.compute_signable_bytes() == grant_b.compute_signable_bytes()
    assert grant_a.signature_hex == grant_b.signature_hex


# ---------------------------------------------------------------------------
# Verification & Fail-Closed Enforcement
# ---------------------------------------------------------------------------

def test_verify_grant_success(creator_identity, authority):
    grant = create_authority_grant(
        creator_identity,
        action=CreatorActionType.REOPEN,
        target="M2.8",
    )
    assert authority.verify_grant(grant, expected_action="reopen", expected_target="M2.8") is True
    # authorize_action raises nothing on success
    authority.authorize_action(grant, expected_action="reopen", expected_target="M2.8")


def test_tampered_signature_rejected_with_authority_unavailable(creator_identity, authority):
    grant = create_authority_grant(
        creator_identity,
        action=CreatorActionType.REOPEN,
        target="M2.8",
    )
    # Tamper with the signature (flip a character)
    tampered_sig = ("0" if grant.signature_hex[0] != "0" else "1") + grant.signature_hex[1:]
    tampered_grant = grant.model_copy(update={"signature_hex": tampered_sig})

    assert authority.verify_grant(tampered_grant) is False
    with pytest.raises(AuthorityUnavailable) as exc_info:
        authority.authorize_action(tampered_grant, expected_action="reopen", expected_target="M2.8")
    assert "signature verification failed" in str(exc_info.value).lower()


def test_forged_key_rejected_with_authority_unavailable(authority, tmp_path):
    # Attacker keypair
    attacker_identity = CreatorIdentity.create(tmp_path / "attacker_keys")
    forged_grant = create_authority_grant(
        attacker_identity,
        action=CreatorActionType.REOPEN,
        target="M2.8",
    )

    assert authority.verify_grant(forged_grant) is False
    with pytest.raises(AuthorityUnavailable) as exc_info:
        authority.authorize_action(forged_grant, expected_action="reopen", expected_target="M2.8")
    assert "does not match authority fingerprint" in str(exc_info.value)


def test_mismatched_action_rejected_with_authority_unavailable(creator_identity, authority):
    grant = create_authority_grant(
        creator_identity,
        action=CreatorActionType.REOPEN,
        target="M2.8",
    )
    with pytest.raises(AuthorityUnavailable) as exc_info:
        authority.authorize_action(grant, expected_action="merge_proposal", expected_target="M2.8")
    assert "does not match expected action" in str(exc_info.value)


def test_mismatched_target_rejected_with_authority_unavailable(creator_identity, authority):
    grant = create_authority_grant(
        creator_identity,
        action=CreatorActionType.REOPEN,
        target="M2.8",
    )
    with pytest.raises(AuthorityUnavailable) as exc_info:
        authority.authorize_action(grant, expected_action="reopen", expected_target="M2.9")
    assert "does not match expected target" in str(exc_info.value)


def test_mismatched_parameters_rejected_with_authority_unavailable(creator_identity, authority):
    grant = create_authority_grant(
        creator_identity,
        action=CreatorActionType.POLICY_OVERRIDE,
        target="circuit_breaker",
        parameters={"threshold": 10},
    )
    with pytest.raises(AuthorityUnavailable) as exc_info:
        authority.authorize_action(
            grant,
            expected_action="policy_override",
            expected_target="circuit_breaker",
            expected_parameters={"threshold": 20},
        )
    assert "parameters" in str(exc_info.value)


def test_malformed_signature_hex_rejected_with_authority_unavailable(creator_identity, authority):
    grant = create_authority_grant(
        creator_identity,
        action=CreatorActionType.REOPEN,
        target="M2.8",
    )
    malformed_grant = grant.model_copy(update={"signature_hex": "not_hex_xyz!"})
    with pytest.raises(AuthorityUnavailable) as exc_info:
        authority.authorize_action(malformed_grant, expected_action="reopen", expected_target="M2.8")
    assert "not valid hex" in str(exc_info.value)


def test_authority_init_missing_key_raises_authority_unavailable(tmp_path):
    empty_dir = tmp_path / "non_existent_keys"
    with pytest.raises(AuthorityUnavailable):
        CryptoAuthority(keys_dir=empty_dir)


def test_authority_init_invalid_public_key_bytes_raises_authority_unavailable():
    with pytest.raises(AuthorityUnavailable) as exc_info:
        CryptoAuthority(creator_public_key=b"too-short")
    assert "invalid creator public key bytes" in str(exc_info.value)


def test_authority_init_unsupported_type_raises_authority_unavailable():
    with pytest.raises(AuthorityUnavailable) as exc_info:
        CryptoAuthority(creator_public_key=12345)  # type: ignore[arg-type]
    assert "unsupported creator public key type" in str(exc_info.value)


def test_authority_load_from_keys_dir(creator_keys_dir, creator_identity):
    auth = CryptoAuthority(keys_dir=creator_keys_dir)
    assert auth.fingerprint == creator_identity.fingerprint()
    assert auth.public_key_bytes == creator_identity.public_key_bytes


# ---------------------------------------------------------------------------
# Creator-Gated Action Helpers
# ---------------------------------------------------------------------------

def test_authorize_reopen(creator_identity, authority):
    grant = create_authority_grant(creator_identity, CreatorActionType.REOPEN, "package-m2")
    authority.authorize_reopen(grant, target="package-m2")

    # Mismatch target
    with pytest.raises(AuthorityUnavailable):
        authority.authorize_reopen(grant, target="package-m3")


def test_authorize_merge_proposal(creator_identity, authority):
    grant = create_authority_grant(creator_identity, CreatorActionType.MERGE_PROPOSAL, "commit-abc123")
    authority.authorize_merge_proposal(grant, target="commit-abc123")

    with pytest.raises(AuthorityUnavailable):
        authority.authorize_merge_proposal(grant, target="commit-xyz789")


def test_authorize_policy_override(creator_identity, authority):
    grant = create_authority_grant(
        creator_identity,
        CreatorActionType.POLICY_OVERRIDE,
        "privacy.redaction",
        parameters={"bypass": True},
    )
    authority.authorize_policy_override(grant, target="privacy.redaction", expected_parameters={"bypass": True})

    with pytest.raises(AuthorityUnavailable):
        authority.authorize_policy_override(grant, target="privacy.redaction", expected_parameters={"bypass": False})


# ---------------------------------------------------------------------------
# NAT-02 Second Half: Cryptographic Capability Registry
# ---------------------------------------------------------------------------

def test_nat_02_crypto_registry_registration_succeeds_with_valid_grant(
    creator_identity, authority
):
    binding = _sample_binding("test.provider.valid")
    grant = create_authority_grant(
        creator_identity,
        CreatorActionType.PROVIDER_REGISTRATION,
        target="test.provider.valid",
    )

    crypto_reg = CryptoCapabilityRegistry(authority=authority)
    crypto_reg.register_provider(binding, grant)

    assert crypto_reg.has_contract("test.provider.valid.echo", "1.0.0")
    assert crypto_reg.get_provider("test.provider.valid") is not None
    assert crypto_reg.resolve_provider("test.provider.valid.echo", "1.0.0") == "test.provider.valid"


def test_nat_02_crypto_registry_registration_fails_on_forged_grant(authority, tmp_path):
    attacker = CreatorIdentity.create(tmp_path / "attacker")
    binding = _sample_binding("test.provider.forged")
    forged_grant = create_authority_grant(
        attacker,
        CreatorActionType.PROVIDER_REGISTRATION,
        target="test.provider.forged",
    )

    crypto_reg = CryptoCapabilityRegistry(authority=authority)
    with pytest.raises(AuthorityUnavailable) as exc_info:
        crypto_reg.register_provider(binding, forged_grant)

    assert "does not match authority fingerprint" in str(exc_info.value)
    # NAT-02: Registry remains completely unchanged
    assert crypto_reg.get_provider("test.provider.forged") is None
    assert crypto_reg.list_contracts() == []


def test_nat_02_crypto_registry_registration_fails_on_tampered_grant(
    creator_identity, authority
):
    binding = _sample_binding("test.provider.tampered")
    grant = create_authority_grant(
        creator_identity,
        CreatorActionType.PROVIDER_REGISTRATION,
        target="test.provider.tampered",
    )
    tampered_grant = grant.model_copy(
        update={"signature_hex": "a" * 128}
    )

    crypto_reg = CryptoCapabilityRegistry(authority=authority)
    with pytest.raises(AuthorityUnavailable):
        crypto_reg.register_provider(binding, tampered_grant)

    assert crypto_reg.get_provider("test.provider.tampered") is None
    assert crypto_reg.list_contracts() == []


def test_nat_02_crypto_registry_registration_fails_on_mismatched_provider_id(
    creator_identity, authority
):
    binding = _sample_binding("test.provider.real")
    # Grant authorizes a different provider
    grant = create_authority_grant(
        creator_identity,
        CreatorActionType.PROVIDER_REGISTRATION,
        target="test.provider.different",
    )

    crypto_reg = CryptoCapabilityRegistry(authority=authority)
    with pytest.raises(AuthorityUnavailable) as exc_info:
        crypto_reg.register_provider(binding, grant)

    assert "does not match expected target" in str(exc_info.value)
    assert crypto_reg.get_provider("test.provider.real") is None


def test_crypto_registry_revocation_succeeds_with_valid_grant(
    creator_identity, authority
):
    binding = _sample_binding("test.provider.revocable")
    reg_grant = create_authority_grant(
        creator_identity,
        CreatorActionType.PROVIDER_REGISTRATION,
        target="test.provider.revocable",
    )
    crypto_reg = CryptoCapabilityRegistry(authority=authority)
    crypto_reg.register_provider(binding, reg_grant)
    assert crypto_reg.get_provider("test.provider.revocable") is not None

    rev_grant = create_authority_grant(
        creator_identity,
        CreatorActionType.PROVIDER_REVOCATION,
        target="test.provider.revocable",
    )
    crypto_reg.revoke_provider("test.provider.revocable", rev_grant)
    assert crypto_reg.get_provider("test.provider.revocable") is None


def test_crypto_registry_revocation_fails_on_tampered_grant(
    creator_identity, authority
):
    binding = _sample_binding("test.provider.keep")
    reg_grant = create_authority_grant(
        creator_identity,
        CreatorActionType.PROVIDER_REGISTRATION,
        target="test.provider.keep",
    )
    crypto_reg = CryptoCapabilityRegistry(authority=authority)
    crypto_reg.register_provider(binding, reg_grant)

    rev_grant = create_authority_grant(
        creator_identity,
        CreatorActionType.PROVIDER_REVOCATION,
        target="test.provider.keep",
    )
    tampered_rev_grant = rev_grant.model_copy(update={"signature_hex": "0" * 128})

    with pytest.raises(AuthorityUnavailable):
        crypto_reg.revoke_provider("test.provider.keep", tampered_rev_grant)

    # Provider still present
    assert crypto_reg.get_provider("test.provider.keep") is not None


def test_crypto_registry_unconfigured_authority_raises_authority_unavailable(creator_identity):
    crypto_reg = CryptoCapabilityRegistry(authority=None)
    binding = _sample_binding("test.provider.noauth")
    grant = create_authority_grant(
        creator_identity,
        CreatorActionType.PROVIDER_REGISTRATION,
        target="test.provider.noauth",
    )
    with pytest.raises(AuthorityUnavailable) as exc_info:
        crypto_reg.register_provider(binding, grant)
    assert "no CryptoAuthority configured" in str(exc_info.value)
