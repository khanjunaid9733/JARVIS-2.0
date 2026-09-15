from __future__ import annotations

"""Capability registry (module 4).

Implements the `ContractCatalog` protocol consumed by `intent.validate_proposal`
(module 3) as an event-sourced projection over `capability.*` events (spec
§125, §131.2–131.5, ADR-001/003/007).

Reconstructed state is a pure function of the event log: every mutation is a
logged event, so `from_log()` yields the identical provider set on any restart
(§127.1 "the registry reflects exactly the seeded providers"). The projection
never trusts additions — it replays the verified chain.

M1 event vocabulary handled here (spec §131.5 subset):

  capability.provider_proposed   any principal; creates a NON-usable record
  capability.provider_added      creator only, signed approval; activates (§105.2)
  capability.provider_deprecated creator only; contract stays resolveable
  capability.provider_revoked    creator only; cannot receive new work

Explicitly OUT of M1 scope (documented, not stubbed with no-ops):
  capability.resolved            runtime routing decision (module 6/7)
  capability.provider_health_changed  (module 6 monitoring)
  capability.contract_versioned / capability.adapter_registered
  capability.provider_promoted   model/provider promotion lifecycle

Design decisions (resolved ambiguities):

1. Authority gate (ADR-003/007): `provider_added|deprecated|revoked` are
   creator-only. The proof is a detached Ed25519 signature embedded in the
   event payload under "approval", plus the principal_id = creator
   fingerprint. Replay validates the signature against the registry's bound
   creator key and FAILS CLOSED with RegistryAuthorityError on any invalid
   or failed-signed authority event (NAT-02: registry unchanged).

2. What exactly is signed — deviation from creator.export_signable:
   creator.py's `export_signable(event_id, event_sha256)` signs the host
   event's chain identity. That byte string cannot be embedded in the same
   event's payload because event_sha256 covers payload_sha256 (circular).
   M1 therefore signs the canonical payload content WITHOUT the "approval"
   key, wrapped in the sac envelope `jarvis-authority-v1` with the event
   type. The resulting signature lives in the payload; the chain hash then
   covers the embedded signature, so both the authority proof and the
   EventLog chain integrity bound the same bytes. Recompute is deterministic
   on replay. Verified: creator.verify_with(anchor, signable, signature).

3. Signature verification key: the registry binds exactly one creator public
   key (its trust anchor). A valid signature from a DIFFERENT key is
   rejected — the anchor cannot be swapped by a logged event in M1 (manual
   regeneration + re-registration per ADR-007).

4. Usability states: "proposed" providers are never resolveable (§105.2:
   "the registry is unusable for a proposed provider until step 2");
   "revoked" providers cannot receive new work (§131.7.14) and are not
   resolveable; "deprecated" providers remain resolveable while the contract
   stays live (§131.3). Candidate set for resolution = {active, deprecated}.

5. Contract schema when multiple providers declare the same
   (contract_id, version): the registry is authoritative over the INTENT
   ABI, so get_args_schema must return ONE schema. Deterministic pick:
   among usable providers declaring that contract at that resolved version,
   the lexicographically smallest provider_id wins. Seeded providers do not
   overlap in M1; the rule exists for containment.

6. Version constraint dialect (M1, matches module-3 usage "^1.0"):
   - exact: "1.0", "1.0.0"
   - caret: "^1.0", "^1.0.0"  (same major; same minor when given)
   - wildcard: "*" or ""      (any version; highest wins)
   Resolution is deterministic: numeric parts compared as integers, then
   remaining parts lexically; the highest satisfying version wins.

7. Registration metadata gate (§131.4): `add` refuses metadata missing any
   required supply-chain field (ProviderMetadataError) — "registration MUST
   be blocked ... if required supply-chain fields are absent".

8. Seeding (§105.1): `seed()` appends four `capability.provider_added`
   events — filesystem, terminal, one local model adapter, HTTP client —
   each with full supply-chain metadata and signed by the creator. These are
   metadata declarations only; adapters/effects are modules 5–8.

9. Transactional shape: a live registry handle appends the event to the log
   FIRST, then immediately replays the chain to re-project itself. The
   authoritative state is always a function of the log; the live handle never
   mutates provider state out-of-band.
"""

import datetime as _dt
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .creator import CreatorIdentity
from .event_log import Event, EventLog, _canonical_json, new_ulid
from .intent import ContractCatalog


def _now_utc_iso() -> str:
    return (
        _dt.datetime.now(_dt.timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class RegistryError(RuntimeError):
    """Base error for the capability registry."""


class RegistryAuthorityError(RegistryError):
    """Typed authority failure. Raised when an authority event is proposed by
    a non-creator principal, unsigned, or signed by a different key. NAT-02."""

    def __init__(self, message: str, *, event: Event | None = None) -> None:
        super().__init__(message)
        self.event = event


class ProviderMetadataError(RegistryError):
    """Typed rejection when required supply-chain metadata is absent (§131.4)."""


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

ProviderStatus = str  # "proposed" | "active" | "deprecated" | "revoked"


class ContractDecl(BaseModel):
    """A capability contract served by a provider. Args schema uses the M1
    dialect defined in intent.py so get_args_schema feeds validate_proposal."""

    model_config = ConfigDict(extra="forbid")

    contract_id: str
    version: str = "1.0.0"
    description: str = ""
    args_schema: dict[str, Any] = Field(default_factory=dict)


class ProviderMetadata(BaseModel):
    """Supply-chain metadata, §131.4 minimum required fields."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    repo: str | None = None
    version: str = "1.0.0"
    commit: str | None = None
    license: str
    license_compatibility: str
    adapter: str
    trust_level: str
    process_model: str
    network_scope: str
    cve_status: str
    last_audit: str
    health_check: str
    fallback: list[str] = Field(default_factory=list)
    description: str = ""


class _Registration(BaseModel):
    """Provenance of registration (§131.4 provenance + §105.2 two-step)."""

    model_config = ConfigDict(extra="forbid")

    proposed_by: str | None = None
    proposed_at: str | None = None
    proposal_event_id: str | None = None
    added_by: str | None = None
    added_at: str | None = None
    add_event_id: str | None = None


class ProviderRecord(BaseModel):
    """Projected provider state."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    status: ProviderStatus
    metadata: ProviderMetadata
    contracts: list[ContractDecl] = Field(default_factory=list)
    registration: _Registration = Field(default_factory=_Registration)


# ---------------------------------------------------------------------------
# Signing helpers (decision #2 in module docstring)
# ---------------------------------------------------------------------------

SAC_ENVELOPE = "jarvis-authority-v1"

APPROVAL_KEY = "approval"


def _authority_signable(event_type: str, payload_without_approval: dict[str, Any]) -> bytes:
    """Canonical bytes the creator signs for an authority event. Covers the
    payload minus the approval key, wrapped in the sac envelope."""
    return _canonical_json(
        {
            "sac": SAC_ENVELOPE,
            "event_type": event_type,
            "provider": payload_without_approval,
        }
    )


def _make_approval(
    creator: CreatorIdentity,
    event_type: str,
    payload_without_approval: dict[str, Any],
) -> dict[str, str]:
    """Build the approval blob: creator fingerprint + detached signature."""
    signature = creator.sign(_authority_signable(event_type, payload_without_approval))
    return {
        "fingerprint": creator.fingerprint(),
        "signature_hex": signature.hex(),
    }


def _signature_valid(
    public_key_bytes: bytes,
    event_type: str,
    payload_without_approval: dict[str, Any],
    approval: dict[str, Any],
) -> bool:
    signature_hex = approval.get("signature_hex")
    if not isinstance(signature_hex, str) or not signature_hex:
        return False
    try:
        signature = bytes.fromhex(signature_hex)
    except (TypeError, ValueError):
        return False
    return CreatorIdentity.verify_with(
        public_key_bytes,
        _authority_signable(event_type, payload_without_approval),
        signature,
    )


def _payload_without_approval(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k != APPROVAL_KEY}


# ---------------------------------------------------------------------------
# Version resolution (§131.2 + decision #6)
# ---------------------------------------------------------------------------

def _version_key(version: str) -> tuple[tuple[int, ...], tuple[str, ...]]:
    """Deterministic sort key: integer parts first, remaining parts lexical."""
    integers: list[int] = []
    strings: list[str] = []
    for part in version.split("."):
        if part.isdigit():
            integers.append(int(part))
        else:
            strings.append(part)
    return (tuple(integers), tuple(strings))


def _matches_constraint(version: str, constraint: str) -> bool:
    constraint = constraint.strip()
    if constraint in ("", "*"):
        return True
    if constraint.startswith("^"):
        prefix = constraint[1:]
        return version == prefix or version.startswith(prefix + ".")
    # exact
    return version == constraint


def _highest(versions: list[str], constraint: str) -> str | None:
    candidates = sorted(
        (v for v in versions if _matches_constraint(v, constraint)),
        key=_version_key,
    )
    return candidates[-1] if candidates else None


_MINIMUM_METADATA_FIELDS: dict[str, str] = {
    "provider_id": "provider identity",
    "license": "license",
    "license_compatibility": "license compatibility",
    "adapter": "adapter identity",
    "trust_level": "trust/isolation level",
    "process_model": "process model",
    "network_scope": "required network/filesystem scope",
    "cve_status": "CVE/security status",
    "last_audit": "last audit",
    "health_check": "health-check definition",
}


def _assert_metadata_complete(metadata: ProviderMetadata) -> None:
    missing = [
        label
        for field, label in _MINIMUM_METADATA_FIELDS.items()
        if getattr(metadata, field) in (None, "")
    ]
    if missing:
        raise ProviderMetadataError(
            f"provider '{metadata.provider_id}' missing required supply-chain "
            f"metadata: {', '.join(missing)}"
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class CapabilityRegistry(ContractCatalog):
    """Event-sourced projection implementing the intent ABI's ContractCatalog.

    Construct live via `CapabilityRegistry(creator)` for writes + reads, or
    `CapabilityRegistry.from_log(log, creator)` to rebuild from a chain
    (constructor arg `creator_public_key_bytes` is the replay-only path).
    All mutations append events to the log; provider state is re-projected
    from the replayed chain (decision #9).
    """

    def __init__(
        self,
        creator: CreatorIdentity | None = None,
        *,
        creator_public_key_bytes: bytes | None = None,
    ) -> None:
        if creator is not None:
            self._anchor = creator.public_key_bytes
        elif creator_public_key_bytes is not None:
            self._anchor = creator_public_key_bytes
        else:
            raise TypeError(
                "CapabilityRegistry requires creator or creator_public_key_bytes"
            )
        self._providers: dict[str, ProviderRecord] = {}
        self._proposed: dict[str, ProviderRecord] = {}

    # ---- construction -----------------------------------------------------

    @classmethod
    def from_log(
        cls,
        log: EventLog,
        creator: CreatorIdentity | None = None,
        *,
        creator_public_key_bytes: bytes | None = None,
    ) -> "CapabilityRegistry":
        """Replay the chain and project `capability.*` events (NAT-03/04
        compatible: uses EventLog.replay(), which halts on integrity failure).
        Raises RegistryAuthorityError on any invalid authority event."""
        if creator is not None:
            pub = creator.public_key_bytes
        elif creator_public_key_bytes is not None:
            pub = creator_public_key_bytes
        else:
            raise TypeError(
                "from_log requires creator or creator_public_key_bytes"
            )
        registry = cls(creator_public_key_bytes=pub)
        for event in log.replay():
            registry._apply(event, pub)
        return registry

    # ---- event application (projection) ----------------------------------

    def _apply(self, event: Event, anchor: bytes) -> None:
        event_type = event.event_type
        if not event_type.startswith("capability."):
            return

        if event_type == "capability.provider_proposed":
            self._apply_proposed(event)
            return

        if event_type == "capability.provider_added":
            self._apply_added(event, anchor)
            return

        if event_type in {"capability.provider_deprecated", "capability.provider_revoked"}:
            self._apply_transition(event, anchor)
            return

        # Unknown capability.* event types are ignored (forward compat), not
        # fatal — out-of-scope M1 events are documented in the module
        # docstring.

    def _parse_provider_event(
        self, body: dict[str, Any], event_type: str, seq: int | None
    ) -> tuple[ProviderMetadata, list[ContractDecl]]:
        try:
            metadata = ProviderMetadata(
                **{k: v for k, v in body.items() if k != "contracts"}
            )
            contracts = [
                ContractDecl(**decl) for decl in body.get("contracts", [])
            ]
        except Exception as exc:  # pydantic ValidationError et al.
            raise RegistryError(
                f"malformed {event_type} at seq={seq}: {exc}"
            ) from exc
        return metadata, contracts

    def _apply_proposed(self, event: Event) -> None:
        body = _payload_without_approval(event.payload)
        metadata, contracts = self._parse_provider_event(
            body, event.event_type, event.stream_seq
        )
        self._proposed[metadata.provider_id] = ProviderRecord(
            provider_id=metadata.provider_id,
            status="proposed",
            metadata=metadata,
            contracts=contracts,
            registration=_Registration(
                proposed_by=event.principal_id,
                proposed_at=event.ts_utc,
                proposal_event_id=event.event_id,
            ),
        )

    def _verify_authority(self, event: Event, anchor: bytes) -> dict[str, Any]:
        payload = event.payload
        approval = payload.get(APPROVAL_KEY)
        if not isinstance(approval, dict):
            raise RegistryAuthorityError(
                f"{event.event_type} without approval at seq={event.stream_seq}",
                event=event,
            )
        body = _payload_without_approval(payload)
        if not _signature_valid(anchor, event.event_type, body, approval):
            raise RegistryAuthorityError(
                f"{event.event_type} with invalid creator signature at "
                f"seq={event.stream_seq} (event_id={event.event_id})",
                event=event,
            )
        return body

    def _apply_added(self, event: Event, anchor: bytes) -> None:
        body = self._verify_authority(event, anchor)
        metadata, contracts = self._parse_provider_event(
            body, event.event_type, event.stream_seq
        )
        prior = self._proposed.pop(metadata.provider_id, None)
        self._providers[metadata.provider_id] = ProviderRecord(
            provider_id=metadata.provider_id,
            status="active",
            metadata=metadata,
            contracts=contracts,
            registration=_Registration(
                proposed_by=(
                    prior.registration.proposed_by if prior else None
                ),
                proposed_at=(
                    prior.registration.proposed_at if prior else None
                ),
                proposal_event_id=(
                    prior.registration.proposal_event_id if prior else None
                ),
                added_by=event.principal_id,
                added_at=event.ts_utc,
                add_event_id=event.event_id,
            ),
        )

    def _apply_transition(self, event: Event, anchor: bytes) -> None:
        body = self._verify_authority(event, anchor)
        provider_id = body.get("provider_id")
        record = self._providers.get(provider_id) if provider_id is not None else None
        if record is None:
            raise RegistryAuthorityError(
                f"{event.event_type} for unknown provider "
                f"{provider_id!r} at seq={event.stream_seq}",
                event=event,
            )
        if event.event_type == "capability.provider_deprecated":
            new_status = "deprecated"
        else:  # capability.provider_revoked
            new_status = "revoked"
        self._providers[provider_id] = record.model_copy(
            update={"status": new_status}
        )

    # ---- mutation (live writes) -------------------------------------------

    def _append_and_reproject(
        self, log: EventLog, event: Event
    ) -> str:
        """Append then re-project the chain so the live handle matches the
        log's authoritative state."""
        event_id = log.append(event)
        self._providers.clear()
        self._proposed.clear()
        for replayed in log.replay():
            self._apply(replayed, self._anchor)
        return event_id

    def propose(
        self,
        log: EventLog,
        principal_id: str,
        metadata: ProviderMetadata,
        contracts: list[ContractDecl],
    ) -> str:
        """Step 1 of §105.2: any principal may propose a provider. The record
        is NOT usable until provider_added."""
        return self._append_and_reproject(
            log,
            Event(
                event_id=new_ulid(),
                stream_id="capability",
                event_type="capability.provider_proposed",
                schema_version=1,
                principal_id=principal_id,
                ts_utc=_now_utc_iso(),
                payload={
                    **metadata.model_dump(),
                    "contracts": [c.model_dump() for c in contracts],
                },
            ),
        )

    def add(
        self,
        log: EventLog,
        creator: CreatorIdentity,
        metadata: ProviderMetadata,
        contracts: list[ContractDecl],
    ) -> str:
        """Step 2 of §105.2: creator-only activation with signed approval.
        Refuses metadata missing required supply-chain fields (§131.4)."""
        _assert_metadata_complete(metadata)
        if creator.public_key_bytes != self._anchor:
            raise RegistryAuthorityError(
                "submitted creator public key does not match registry anchor"
            )

        event_type = "capability.provider_added"
        payload: dict[str, Any] = {
            **metadata.model_dump(),
            "contracts": [c.model_dump() for c in contracts],
        }
        payload[APPROVAL_KEY] = _make_approval(creator, event_type, payload)

        return self._append_and_reproject(
            log,
            Event(
                event_id=new_ulid(),
                stream_id="capability",
                event_type=event_type,
                schema_version=1,
                principal_id=creator.fingerprint(),
                ts_utc=_now_utc_iso(),
                payload=payload,
            ),
        )

    def deprecate(
        self, log: EventLog, creator: CreatorIdentity, provider_id: str
    ) -> str:
        return self._authority_transition(
            log, creator, provider_id, "capability.provider_deprecated"
        )

    def revoke(
        self, log: EventLog, creator: CreatorIdentity, provider_id: str
    ) -> str:
        return self._authority_transition(
            log, creator, provider_id, "capability.provider_revoked"
        )

    def _authority_transition(
        self,
        log: EventLog,
        creator: CreatorIdentity,
        provider_id: str,
        event_type: str,
    ) -> str:
        if creator.public_key_bytes != self._anchor:
            raise RegistryAuthorityError(
                "submitted creator public key does not match registry anchor"
            )
        if provider_id not in self._providers:
            raise RegistryError(
                f"unknown provider '{provider_id}' for {event_type}"
            )

        payload: dict[str, Any] = {"provider_id": provider_id}
        payload[APPROVAL_KEY] = _make_approval(creator, event_type, payload)

        return self._append_and_reproject(
            log,
            Event(
                event_id=new_ulid(),
                stream_id="capability",
                event_type=event_type,
                schema_version=1,
                principal_id=creator.fingerprint(),
                ts_utc=_now_utc_iso(),
                payload=payload,
            ),
        )

    def seed(
        self,
        log: EventLog,
        creator: CreatorIdentity,
        *,
        last_audit: str,
    ) -> list[str]:
        """§105.1: seed the curated 4 providers."""
        event_ids = []
        for metadata, contracts in _SEED_PROVIDERS(last_audit):
            event_ids.append(self.add(log, creator, metadata, contracts))
        return event_ids

    # ---- ContractCatalog (module 3) --------------------------------------

    def _usable_candidates(
        self, contract_id: str
    ) -> list[tuple[ProviderRecord, ContractDecl]]:
        candidates: list[tuple[ProviderRecord, ContractDecl]] = []
        for record in self._providers.values():
            if record.status not in {"active", "deprecated"}:
                continue
            for decl in record.contracts:
                if decl.contract_id == contract_id:
                    candidates.append((record, decl))
        return candidates

    def has_contract(self, contract_id: str, version_constraint: str) -> bool:
        return self.resolve_version(contract_id, version_constraint) is not None

    def resolve_version(self, contract_id: str, version_constraint: str) -> str | None:
        versions = [decl.version for _, decl in self._usable_candidates(contract_id)]
        return _highest(versions, version_constraint)

    def get_args_schema(
        self, contract_id: str, resolved_version: str
    ) -> dict[str, Any]:
        """Deterministic pick: smallest provider_id among usable providers
        declaring (contract_id, resolved_version)."""
        pick: tuple[str, ContractDecl] | None = None
        for record, decl in self._usable_candidates(contract_id):
            if decl.version != resolved_version:
                continue
            if pick is None or record.provider_id < pick[0]:
                pick = (record.provider_id, decl)
        return pick[1].args_schema if pick is not None else {}

    # ---- introspection ----------------------------------------------------

    def providers(self) -> list[ProviderRecord]:
        return [self._providers[p] for p in sorted(self._providers)]

    def proposed_providers(self) -> list[ProviderRecord]:
        return [self._proposed[p] for p in sorted(self._proposed)]

    def provider(self, provider_id: str) -> ProviderRecord | None:
        return self._providers.get(provider_id)


# ---------------------------------------------------------------------------
# Seeding (§105.1)
# ---------------------------------------------------------------------------

def _SEED_PROVIDERS(
    last_audit: str,
) -> list[tuple[ProviderMetadata, list[ContractDecl]]]:
    return [
        (
            ProviderMetadata(
                provider_id="fs.local",
                repo="https://github.com/jarvis/filesystem",
                version="1.0.0",
                commit="0000000000000000000000000000000000000000",
                license="MIT",
                license_compatibility="approved",
                adapter="jarvis.adapters.filesystem",
                trust_level="sandboxed",
                process_model="in-process",
                network_scope="none",
                cve_status="checked",
                last_audit=last_audit,
                health_check="fs.local: path writable probe",
                fallback=[],
                description="Local filesystem read/write/list provider",
            ),
            [
                ContractDecl(
                    contract_id="fs.read",
                    version="1.0.0",
                    description="Read a file's contents by path",
                    args_schema={
                        "path": {"type": "string", "required": True},
                    },
                ),
                ContractDecl(
                    contract_id="fs.write",
                    version="1.0.0",
                    description="Write content to a path",
                    args_schema={
                        "path": {"type": "string", "required": True},
                        "content": {"type": "string", "required": True},
                    },
                ),
                ContractDecl(
                    contract_id="fs.list",
                    version="1.0.0",
                    description="List directory entries",
                    args_schema={
                        "path": {"type": "string", "required": False},
                    },
                ),
            ],
        ),
        (
            ProviderMetadata(
                provider_id="terminal.local",
                repo="https://github.com/jarvis/terminal",
                version="1.0.0",
                commit="0000000000000000000000000000000000000000",
                license="MIT",
                license_compatibility="approved",
                adapter="jarvis.adapters.terminal",
                trust_level="sandboxed",
                process_model="isolated_subprocess",
                network_scope="none",
                cve_status="checked",
                last_audit=last_audit,
                health_check="terminal.local: echo probe",
                fallback=[],
                description="Isolated command execution provider",
            ),
            [
                ContractDecl(
                    contract_id="terminal.run",
                    version="1.0.0",
                    description="Run a command in an isolated subprocess",
                    args_schema={
                        "command": {"type": "string", "required": True},
                        "timeout_s": {"type": "integer", "required": False},
                    },
                ),
            ],
        ),
        (
            ProviderMetadata(
                provider_id="model.local",
                repo="https://github.com/jarvis/model-adapter",
                version="1.0.0",
                commit="0000000000000000000000000000000000000000",
                license="MIT",
                license_compatibility="approved",
                adapter="jarvis.adapters.model",
                trust_level="sandboxed",
                process_model="isolated_subprocess",
                network_scope="localhost_only",
                cve_status="checked",
                last_audit=last_audit,
                health_check="model.local: health endpoint probe",
                fallback=[],
                description="Local model adapter provider (Ollama-capable)",
            ),
            [
                ContractDecl(
                    contract_id="model.generate",
                    version="1.0.0",
                    description="Free-form generation (unstructured)",
                    args_schema={
                        "prompt": {"type": "string", "required": True},
                        "max_tokens": {"type": "integer", "required": False},
                    },
                ),
                ContractDecl(
                    contract_id="model.generate_structured",
                    version="1.0.0",
                    description="Schema-constrained generation (ADR-006)",
                    args_schema={
                        "prompt": {"type": "string", "required": True},
                        "schema": {"type": "object", "required": True},
                    },
                ),
            ],
        ),
        (
            ProviderMetadata(
                provider_id="http.client",
                repo="https://github.com/jarvis/http-client",
                version="1.0.0",
                commit="0000000000000000000000000000000000000000",
                license="MIT",
                license_compatibility="approved",
                adapter="jarvis.adapters.http",
                trust_level="sandboxed",
                process_model="in-process",
                network_scope="egress_only",
                cve_status="checked",
                last_audit=last_audit,
                health_check="http.client: egress deny by default",
                fallback=[],
                description="HTTP client provider (egress only)",
            ),
            [
                ContractDecl(
                    contract_id="http.get",
                    version="1.0.0",
                    description="Perform an HTTP GET request",
                    args_schema={
                        "url": {"type": "string", "required": True},
                    },
                ),
                ContractDecl(
                    contract_id="http.post",
                    version="1.0.0",
                    description="Perform an HTTP POST request",
                    args_schema={
                        "url": {"type": "string", "required": True},
                        "body": {"type": "object", "required": False},
                    },
                ),
            ],
        ),
    ]