# JARVIS — Architecture Decision Record

## Decision: External Capability Substitution Seam

**Status:** ACCEPTED / ARCHITECTURE INVARIANT

All external tools, services, model-serving systems, and capability providers are accessed through versioned semantic contracts.

No JARVIS code may import an external provider directly.

Provider-specific behavior is isolated behind JARVIS-owned adapters and registry-controlled bindings.

### Required shape

```text
JARVIS CODE
    ↓
CAPABILITY CONTRACT
    ↓
CAPABILITY REGISTRY
    ↓
JARVIS-OWNED PROVIDER ADAPTER
    ↓
EXTERNAL PROVIDER
```

The same substitution pattern applies to models:

```text
MODEL ROLE CONTRACT
    ↓
MODEL REGISTRY
    ↓
MODEL ADAPTER
    ↓
MODEL PROVIDER / SERVING BACKEND
```

### Consequences

- External providers remain replaceable.
- Supply-chain metadata is centralized.
- Provider health, provenance, licensing, and security status are auditable.
- Provider failures map into the canonical failure taxonomy.
- Fallback chains can be selected without changing upstream cognitive logic.
- External repositories cannot become architectural dependencies of the kernel.
- Every provider executes outside the canonical kernel process.
- Adding a new repository must not require changing the kernel contract.

### Examples

Browser Use → Playwright can replace one another behind `browser.*` contracts.

LiteLLM is an adapter/provider-side component behind the JARVIS Model Gateway, not the owner of JARVIS routing policy.

vLLM is a model-serving backend, not the model gateway.

Langfuse and Evidently are observability/evaluation subscribers, not critical-path dependencies.

Qdrant is a retrieval index behind the Memory API, not canonical memory.

### Invariant

> Stable semantic contracts above replaceable providers.

This decision is mandatory for all future integrations.

## Decision: Manifest synthesis is model-proposed, determinism-disposed

**Status:** ACCEPTED / ARCHITECTURE INVARIANT

Intents compile into manifests through a model-proposed, deterministically-
validated pipeline. The model proposes contracts; it never selects providers,
never grants capabilities, never bypasses validation.

**Consequence:** Manifest synthesis is testable, replayable, and cannot be
used as a privilege escalation path. Model hallucination in manifest
synthesis produces `intent.rejected`, not unauthorized effects.

---

## Decision: Provider registration requires creator authority

**Status:** ACCEPTED / ARCHITECTURE INVARIANT

Only the creator principal may emit `capability.provider_added`. Agents may
propose. No principal may self-register or self-grant.

**Consequence:** The registry's trust anchor is the creator keypair. It
cannot be expanded by a compromised agent.

---

## Decision: Capability contracts are lower bounds, not equivalences

**Status:** ACCEPTED / ARCHITECTURE INVARIANT

A contract declares minimum guarantees. Adapters declare behavioral profiles.
Substitution is successful only when the contract lower bound and all current
callers' strict requirements are met. Degraded substitution is visible in
provenance, never silent.

**Consequence:** Provider replacement is honest about what changes.
