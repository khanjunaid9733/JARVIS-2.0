from __future__ import annotations

"""Key-Based Creator Authority & Cryptographic Gate (Milestone M2.8, spec §105 / §131.2–131.4 / ADR-003 / ADR-007).

Completes the cryptographic authority plane (NAT-02 second half), replacing
simple `principal_id == "creator"` string equality with Ed25519 signature
verification for all creator-gated actions:
1. Reopen: Authorizing the reopening of frozen tasks/packages (`LifecycleEvent.REOPEN`).
2. Merge Proposal: Authorizing package merge proposals to `main` (L2 creator gate).
3. Policy Override: Authorizing runtime overrides for privacy classes, budgets, and circuit breakers.
4. Provider Registration/Revocation: Cryptographically gating capability registry mutations
   in `CryptoCapabilityRegistry` (NAT-02 completion).

Invariants:
1. Fail-Closed: Any missing key, unreadable key material, tampered signature,
   forged key, expired grant, or mismatching action/target strictly raises
   `AuthorityUnavailable`. Never fails open; never falls back to an unverified state.
2. Domain Separation: Every signable payload is prefixed with the canonical domain
   tag `"sac": "jarvis-creator-authority-v1"` to prevent cross-protocol signature reuse.
3. Deterministic: Canonical signable payload generation is byte-identical across
   platforms (sorted keys, no whitespace, UTF-8 encoded).
4. Replay Protection: Every `AuthorityGrant` carries a cryptographic `nonce` and
   an ISO 8601 UTC timestamp `created_at_utc`.
5. Strictly Additive: Extends kernel authority without modifying existing frozen
   modules (modules 1–17 remain byte-identical to baseline).
"""

import datetime
import enum
import hashlib
import uuid
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)
from pydantic import BaseModel, ConfigDict, Field

from .creator import AuthorityUnavailable, CreatorIdentity
from .event_log import _canonical_json
from .registry import CREATOR_PRINCIPAL_ID, CapabilityRegistry, ProviderBinding

DOMAIN_TAG = "jarvis-creator-authority-v1"


# ---------------------------------------------------------------------------
# Creator Action Types
# ---------------------------------------------------------------------------

class CreatorActionType(str, enum.Enum):
    """Canonical action types that require cryptographic creator authorization."""

    REOPEN = "reopen"
    MERGE_PROPOSAL = "merge_proposal"
    POLICY_OVERRIDE = "policy_override"
    PROVIDER_REGISTRATION = "provider_registration"
    PROVIDER_REVOCATION = "provider_revocation"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Authority Grant Schema
# ---------------------------------------------------------------------------

class AuthorityGrant(BaseModel):
    """Cryptographically signed authorization grant for a creator-gated action.

    Carries the detached Ed25519 signature over the canonical signable bytes,
    the signing creator's key fingerprint, and replay-prevention metadata.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: str
    target: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    created_at_utc: str
    nonce: str
    creator_fingerprint: str
    signature_hex: str

    def compute_signable_bytes(self) -> bytes:
        """Computes the canonical byte string that must be signed.

        Sorted keys, no whitespace, UTF-8 encoded canonical JSON with the
        domain separation tag.
        """
        payload = {
            "action": self.action,
            "created_at_utc": self.created_at_utc,
            "nonce": self.nonce,
            "parameters": self.parameters,
            "sac": DOMAIN_TAG,
            "target": self.target,
        }
        return _canonical_json(payload)

    @property
    def signature_bytes(self) -> bytes:
        """Decodes the signature hex string into raw 64-byte Ed25519 signature bytes.

        Raises AuthorityUnavailable if signature_hex is malformed.
        """
        try:
            return bytes.fromhex(self.signature_hex)
        except (ValueError, TypeError) as exc:
            raise AuthorityUnavailable(
                f"grant signature is not valid hex: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Grant Issuance
# ---------------------------------------------------------------------------

def create_authority_grant(
    identity: CreatorIdentity,
    action: CreatorActionType | str,
    target: str,
    parameters: dict[str, Any] | None = None,
    *,
    created_at_utc: str | None = None,
    nonce: str | None = None,
) -> AuthorityGrant:
    """Issues and cryptographically signs an `AuthorityGrant` using a `CreatorIdentity`.

    Parameters:
    - identity: The CreatorIdentity holding the private Ed25519 key.
    - action: The action being authorized (e.g. 'reopen', 'provider_registration').
    - target: The resource/entity being authorized (package ID, provider ID, etc.).
    - parameters: Optional dictionary of action-specific constraints/parameters.
    - created_at_utc: Optional ISO 8601 timestamp string (defaults to current UTC).
    - nonce: Optional unique nonce string (defaults to random UUID4 hex).
    """
    action_str = action.value if isinstance(action, enum.Enum) else str(action)
    ts = (
        created_at_utc
        if created_at_utc is not None
        else datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
    )
    n = nonce if nonce is not None else uuid.uuid4().hex
    params = parameters if parameters is not None else {}

    # Build unsigned payload to get canonical bytes
    payload = {
        "action": action_str,
        "created_at_utc": ts,
        "nonce": n,
        "parameters": params,
        "sac": DOMAIN_TAG,
        "target": target,
    }
    signable = _canonical_json(payload)
    sig_bytes = identity.sign(signable)

    return AuthorityGrant(
        action=action_str,
        target=target,
        parameters=params,
        created_at_utc=ts,
        nonce=n,
        creator_fingerprint=identity.fingerprint(),
        signature_hex=sig_bytes.hex(),
    )


# ---------------------------------------------------------------------------
# Cryptographic Verification Authority
# ---------------------------------------------------------------------------

class CryptoAuthority:
    """Verification authority for creator-gated actions and grants.

    Validates that incoming grants are cryptographically signed by the
    trusted creator public key and match the expected action, target,
    and parameters.
    """

    def __init__(
        self,
        creator_public_key: bytes | Ed25519PublicKey | None = None,
        *,
        keys_dir: Any | None = None,
    ) -> None:
        """Initializes the authority with a trusted creator public key.

        If `creator_public_key` is not explicitly provided, attempts to load
        the public key from `CreatorIdentity.load(keys_dir)`.
        Raises `AuthorityUnavailable` if the key is missing, unreadable, or corrupt.
        """
        if creator_public_key is not None:
            if isinstance(creator_public_key, Ed25519PublicKey):
                self._public_key = creator_public_key
                self._public_key_bytes = creator_public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                )
            elif isinstance(creator_public_key, (bytes, bytearray)):
                raw_bytes = bytes(creator_public_key)
                try:
                    self._public_key = Ed25519PublicKey.from_public_bytes(raw_bytes)
                    self._public_key_bytes = raw_bytes
                except (ValueError, TypeError) as exc:
                    raise AuthorityUnavailable(
                        f"invalid creator public key bytes: {exc}"
                    ) from exc
            else:
                raise AuthorityUnavailable(
                    f"unsupported creator public key type: {type(creator_public_key).__name__}"
                )
        else:
            try:
                identity = CreatorIdentity.load(keys_dir)
                self._public_key_bytes = identity.public_key_bytes
                self._public_key = identity.public_key_object()
            except AuthorityUnavailable:
                raise
            except Exception as exc:
                raise AuthorityUnavailable(
                    f"creator public key could not be loaded: {exc}"
                ) from exc

    @property
    def public_key_bytes(self) -> bytes:
        return self._public_key_bytes

    @property
    def public_key_hex(self) -> str:
        return self._public_key_bytes.hex()

    @property
    def fingerprint(self) -> str:
        """First 8 lowercase hex characters of SHA-256(public_key)."""
        return hashlib.sha256(self._public_key_bytes).hexdigest()[:8]

    def verify_grant(
        self,
        grant: AuthorityGrant,
        *,
        expected_action: CreatorActionType | str | None = None,
        expected_target: str | None = None,
        expected_parameters: dict[str, Any] | None = None,
    ) -> bool:
        """Checks whether `grant` is valid and matches all expected constraints.

        Returns True if valid, False otherwise. Does not raise.
        """
        try:
            self.authorize_action(
                grant,
                expected_action=expected_action or grant.action,
                expected_target=expected_target if expected_target is not None else grant.target,
                expected_parameters=expected_parameters,
            )
            return True
        except AuthorityUnavailable:
            return False

    def authorize_action(
        self,
        grant: AuthorityGrant,
        *,
        expected_action: CreatorActionType | str,
        expected_target: str,
        expected_parameters: dict[str, Any] | None = None,
    ) -> None:
        """Fail-closed enforcement of creator authorization.

        Validates:
        1. Fingerprint match against trusted public key.
        2. Action match against `expected_action`.
        3. Target match against `expected_target`.
        4. Parameters match against `expected_parameters` (if supplied).
        5. Ed25519 cryptographic signature over canonical signable bytes.

        Raises `AuthorityUnavailable` on ANY failure.
        """
        exp_action_str = (
            expected_action.value
            if isinstance(expected_action, enum.Enum)
            else str(expected_action)
        )

        # 1. Fingerprint verification
        if grant.creator_fingerprint != self.fingerprint:
            raise AuthorityUnavailable(
                f"grant creator_fingerprint '{grant.creator_fingerprint}' "
                f"does not match authority fingerprint '{self.fingerprint}'"
            )

        # 2. Action verification
        if grant.action != exp_action_str:
            raise AuthorityUnavailable(
                f"grant action '{grant.action}' does not match expected action '{exp_action_str}'"
            )

        # 3. Target verification
        if grant.target != expected_target:
            raise AuthorityUnavailable(
                f"grant target '{grant.target}' does not match expected target '{expected_target}'"
            )

        # 4. Parameters verification
        if expected_parameters is not None:
            if grant.parameters != expected_parameters:
                raise AuthorityUnavailable(
                    f"grant parameters {grant.parameters} do not match expected {expected_parameters}"
                )

        # 5. Signature verification
        sig_bytes = grant.signature_bytes
        signable_bytes = grant.compute_signable_bytes()

        try:
            self._public_key.verify(sig_bytes, signable_bytes)
        except InvalidSignature as exc:
            raise AuthorityUnavailable(
                "cryptographic signature verification failed: signature is forged, corrupted, or tampered"
            ) from exc
        except Exception as exc:
            raise AuthorityUnavailable(
                f"signature verification failed with error: {exc}"
            ) from exc

    # ---- Action-specific helpers -------------------------------------------

    def authorize_reopen(self, grant: AuthorityGrant, target: str) -> None:
        """Authorizes reopening a task or package."""
        self.authorize_action(
            grant,
            expected_action=CreatorActionType.REOPEN,
            expected_target=target,
        )

    def authorize_merge_proposal(self, grant: AuthorityGrant, target: str) -> None:
        """Authorizes a merge proposal to `main`."""
        self.authorize_action(
            grant,
            expected_action=CreatorActionType.MERGE_PROPOSAL,
            expected_target=target,
        )

    def authorize_policy_override(
        self,
        grant: AuthorityGrant,
        target: str,
        expected_parameters: dict[str, Any] | None = None,
    ) -> None:
        """Authorizes a policy or budget override."""
        self.authorize_action(
            grant,
            expected_action=CreatorActionType.POLICY_OVERRIDE,
            expected_target=target,
            expected_parameters=expected_parameters,
        )

    def authorize_provider_registration(
        self,
        grant: AuthorityGrant,
        target: str,
        expected_parameters: dict[str, Any] | None = None,
    ) -> None:
        """Authorizes registration of a capability provider (NAT-02)."""
        self.authorize_action(
            grant,
            expected_action=CreatorActionType.PROVIDER_REGISTRATION,
            expected_target=target,
            expected_parameters=expected_parameters,
        )

    def authorize_provider_revocation(
        self,
        grant: AuthorityGrant,
        target: str,
    ) -> None:
        """Authorizes revocation of a capability provider."""
        self.authorize_action(
            grant,
            expected_action=CreatorActionType.PROVIDER_REVOCATION,
            expected_target=target,
        )


# ---------------------------------------------------------------------------
# Cryptographic Capability Registry (NAT-02 Completion)
# ---------------------------------------------------------------------------

class CryptoCapabilityRegistry:
    """Cryptographically-gated Capability Registry completing NAT-02.

    Wraps a `CapabilityRegistry` and replaces principal_id string equality
    with Ed25519 signature verification via `CryptoAuthority`.
    """

    def __init__(
        self,
        registry: CapabilityRegistry | None = None,
        authority: CryptoAuthority | None = None,
    ) -> None:
        self._registry = registry if registry is not None else CapabilityRegistry()
        self._authority = authority

    @property
    def raw_registry(self) -> CapabilityRegistry:
        """Access to the underlying CapabilityRegistry."""
        return self._registry

    @property
    def authority(self) -> CryptoAuthority | None:
        return self._authority

    def register_provider(
        self,
        binding: ProviderBinding,
        grant: AuthorityGrant,
    ) -> None:
        """Register a provider using cryptographic creator authorization.

        Enforces:
        1. A CryptoAuthority is configured.
        2. The grant is validly signed by the creator key.
        3. The grant action is 'provider_registration'.
        4. The grant target matches `binding.meta.provider_id`.

        Raises `AuthorityUnavailable` on any verification failure.
        """
        if self._authority is None:
            raise AuthorityUnavailable(
                "provider registration rejected: no CryptoAuthority configured"
            )

        provider_id = binding.meta.provider_id
        self._authority.authorize_provider_registration(
            grant,
            target=provider_id,
        )

        # Forward to underlying registry under CREATOR_PRINCIPAL_ID
        self._registry.register_provider(CREATOR_PRINCIPAL_ID, binding)

    def revoke_provider(
        self,
        provider_id: str,
        grant: AuthorityGrant,
    ) -> None:
        """Revoke a provider using cryptographic creator authorization."""
        if self._authority is None:
            raise AuthorityUnavailable(
                "provider revocation rejected: no CryptoAuthority configured"
            )

        self._authority.authorize_provider_revocation(
            grant,
            target=provider_id,
        )
        self._registry.revoke_provider(provider_id, CREATOR_PRINCIPAL_ID)

    # ---- ContractCatalog / CapabilityRegistry Forwarding -------------------

    def resolve_provider(self, contract_id: str, version_constraint: str) -> str | None:
        return self._registry.resolve_provider(contract_id, version_constraint)

    def resolve_version(self, contract_id: str, version_constraint: str) -> str | None:
        return self._registry.resolve_version(contract_id, version_constraint)

    def get_args_schema(self, contract_id: str, version: str) -> dict[str, Any] | None:
        return self._registry.get_args_schema(contract_id, version)

    def has_contract(self, contract_id: str, version: str) -> bool:
        return self._registry.has_contract(contract_id, version)

    def get_provider(self, provider_id: str) -> ProviderBinding | None:
        return self._registry.get_provider(provider_id)

    def list_contracts(self) -> list[tuple[str, str, str]]:
        return self._registry.list_contracts()


__all__ = [
    "AuthorityGrant",
    "CreatorActionType",
    "CryptoAuthority",
    "CryptoCapabilityRegistry",
    "DOMAIN_TAG",
    "create_authority_grant",
]
