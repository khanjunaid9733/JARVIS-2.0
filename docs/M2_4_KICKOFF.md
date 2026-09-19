# M2.4 — Memory Verification Ladder (rungs 2–3) — kickoff (PROPOSAL)

**Status:** PROPOSAL — ratified once creator accepts items A–E below.
**Parent:** main @ `3ed2f42` (branch `task/m2.4` = `git diff main` → only this file).
**Spec anchors:** `MASTER_BUILD_SPEC.md` §84.4 (verification ladder: cheap
deterministic checks → **semantic verifier** → **independent verifier** for
high-impact memory), §84.2/§84.5 (memory classes: provenance/confidence/source/
timestamp/validity state/retention/supersession links), §84.3 (two-tier
consolidation → M2.3 shipped), §131.14 (provider roles; verification seams),
`docs/M2_KICKOFF.md` M2.4 row.
**Kernel home (proposal):** `src/jarvis/kernel/memory_verify.py` (new, additive) +
additive seam on the module-10 `memory_write.py` path.
**Theme (§84.4, verbatim):** "A semantic memory is still an evidence-backed
belief unless independently established as fact."

---

## 1. Context

M2.1 shipped the cheap rung and the frozen write chain (`memory.write.proposed →
verified → committed`); M2.2 shipped the retrieval seams; M2.3 shipped the
**cheap deterministic rung only** of the §84.4 ladder — its kernel docstring and
the M2.3 kickoff §D state explicitly: *"the semantic verifier and independent
verifier are M2.4"* (M2_3_KICKOFF.md §D / `memory_consolidate.py` docstring).
M2.4 is that next rung.

Everything M2.3 does, M2.4 must keep **byte-identical** on an unchanged log —
the M2.3 fold-content stability ruling (the M2.2/FB-M2.2-3 precedent re-applied
as FB-M2.3-6 and F-M2.3-6) and the M2.2 digest-force precedent (FB-M2.2-3,
F-M2.2-3) hold. **No module 1–17 is modified.** M2.4 is strictly additive:
a new verification module + additive fields on the already-frozen `memory_write`
path, decided by a **DATA** `VerificationPolicy` (decisioning is data, not
branches — the M2.3 ruling applied to verification).

## 2. Contract items A–E (ratify/propose)

### A. Module `src/jarvis/kernel/memory_verify.py`

`MemoryVerifier` (additive, in-kernel, synchronous, hermetic — **no model calls
on the shipped default policy**, no effects, no ambient reads, no CLI). The
verification decision ladder is DATA-proportional to impact (§84.4):

```text
cheap deterministic checks      (M2.1–M2.3, ALREADY SHIPPED)
        ↓
semantic verifier              (this module)
        ↓
independent verifier          (this module, HIGH-impact memories only)
```

`verify(paths: list[str] | None, *, evidence: list[str] | None = None,
policy: VerificationPolicy | None = None) -> VerificationResult` —
deterministic, additive, replay-order-folded from the SAME frozen write chain
M2.3 promotes through; `recall`/`retrieve`/`digest` semantics untouched.

**The ladder is a DATA table, not branches:**

- `VerificationPolicy.ladder: Literal["cheap_only" | "semantic" | "independent"]`
  — which rung runs for a given impact class (data, not dispatch).
- `high_impact_gate: HighImpactRule` — DATA: `rungs` (`semantic` | `independent`),
  `impact_classes` (which memory classes escalate), `checks` (which PASS pins a
  HIGH-impact memory), `independent_min_confidence`, `authority`
  (principal/role that authors the independent verdict).
- `semantic: SemanticRule` — DATA: `verifier_role`, `confidence_floor`,
  `require_source`, `require_timestamp`, `require_provenance`, `retention_default`
  (policy datum; no hardcoded branch).
- `supercede: SupersedeRule` — same-key/same-source contradiction resolution for
  verification-induced conflicts; successor carries supersession link in
  `provenance` (M2.3 provenance precedent); audit outside `MemoryIndex` folds
  (M2.3 supersession-audit rule RE-APPLIED: fold content stable, event moves
  digest/metadata exactly as FB-M2.3-5 accepted).

### B. `VerificationPolicy` — decisioning is DATA

Frozen pydantic `BaseModel` (`extra="forbid"`), fully described:

- `memory_class` (semantic | procedural), `ladder`, `high_impact_gate`
  (HighImpactRule), `semantic` (SemanticRule), `supercede` (SupersedeRule),
  `retention` (TTL/decay/persistent-until-corrected/explicit-forget per §84.5),
  `pii` (policy datum: privacy-sensitive → stricter retention; **PII detection
  seam is M2.5, deferred** — this is just the policy datum declaring the class,
  not PII detection), `principal_id` (default `"creator"` — M2.3 caller-principal
  precedent).
- `audit: bool` — emit `memory.verify.superseded` audit events? (M2.3 audit
  semantics: always bounded, derived from committed provenance; fold-content
  stability precedent holds).

### C. Additive fields on the frozen `memory.write.*` path

Per §84.4 memory classes: provenance/confidence/source/timestamp/**validity
state**/retention/**supersession links**. Each is ADDITIVE to the existing
`memory.write.*` payloads (M2.3 provenance precedent — supersession links are
`provenance.superseded`, never entering folds). `MemoryIndex`/`Memory.recall`
projection folds stay byte-identical on unchanged logs.

### D. Verification proportional to impact (data, not branching)

Every memory.write passes the SAME frozen gate (M2.1 path). HIGH-impact classes
escalate to the semantic/in-dependent rung by `high_impact_gate.rungs` datum —
**no code dispatch on memory identity**.

### E. Seams, tests, determinism

Hermetic: **hold** on the default policy (cheap deterministic rung is the shipped
default; semantic/in-dependent verifier seams are adapter-backed model seams per
§131.14, OPT-IN via explicit `VerificationPolicy` with a provider, never ambient
state reads, never auto-prompt). Determinism: same log + same policy → identical
result; ULID/confidence/validity are outcome fields, not inputsasi. Additive-only;
frozen modules 1–17 byte-identical; no new deps.

---

### F. Integrations (additive)

- `Memory.verify(...)` facade seam on `memory_api.py` (additive method, delegating
  through the frozen write path) — no `MemoryIndex`/`Memory.recall` change.
- No CLI change; `jarvis explain` untouched.

---

## 3. Scope boundaries (do NOT build in M2.4)

- no semantic verifier = no model/LLM calls as a hardcoded default (default seam
  is DATA + hermetic; adapter-backed verifier is opt-in)
- no PII detection seam (M2.5)
- no embedding/rerank provider seam (M2.2 shipped); no effect/FS (M2.6)
- no semantic checkpoints (this is a VERIFIER rung, tied to §84.4 `memory.write.*;
  `memory.consolidate.*` — checkpoints are §86.1/§84.4, M2.10)
- no new dependencies; no schema/DFA changes to `memory.write.*`; frozen modules
  1–17 untouched; `MemoryIndex` folds stay stable (M2.3 fold-stability precedent
  re-applied)

## 4. Entry conditions (gates)

1. `main` @ `3ed2f42` (M2.3 merged, 413 passed) clean, in sync with `origin/main`.
2. Modules 1–17 frozen; additive-only behind a ratified design — in force.
3. This contract ratified by the creator (accept or refine items A–E).

## 5. Sequencing

1. Ratify items A–E (creator) — including the §B/§C seam-shape and the "default
   seam is cheap+hermetic, verifier seams are opt-in adapter-backed" ruling
   (creator choice, analogous to M2.3 R1/R2).
2. Implement on a task branch: `memory_verify.py` + additive seam. Run full suite.
3. Adversarial + independent pass (Freebuff + Antigravity) on the verification
   ladder contracts.
4. Reconcile findings; flip pins; full suite green.
5. Merge to `main` (`--no-ff`), record in `project_state.yaml`, push; do not
   push the branch.

---

## 6. Ratification decision (creator)

- [x] Ratify A–F as written (creator)
- [ ] Amend (list changes) → re-propose
- [ ] Hold

**Rulings requested before implementation:** (R1) promote via the frozen
`MemoryWriter`/`MemoryIndex` path (M2.3 precedent) without changing fold-content
semantics — recommended, vs. dedicated `memory.verify.*` events; (R2) accept
`suspicion`/`supersession` audit events being excluded from `MemoryIndex` folds
(fold-content stability, M2.3 R2 precedent) vs. extend `MemoryIndex`.
