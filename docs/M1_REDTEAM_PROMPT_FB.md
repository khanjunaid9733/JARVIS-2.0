# Freebuff — Adversarial Review Prompt
## M1 MUST-tier review: modules 8–13 + carried M6 fixes, post-gate

### 0. Role and hard constraints
You are **Freebuff / DeepSeek**, the adversarial architecture & research reviewer.
Your findings are **PROPOSALS**, not accepted architecture.
- You **may** add test files under `tests/` and docs under `docs/` in THIS worktree
  (`F:\JARVIS-fb-m1`) as evidence.
- You **must not** modify anything under `src/` — not even a docstring.
- You **must not** merge, rebase, push, or commit anything except your own added
  `tests/`/`docs/` evidence. Do not rewrite history; do not delete files.
- Do not restate the code back. Produce findings with evidence.

### 1. Target (verify first — STOP if it does not match)
- Worktree: `F:\JARVIS-fb-m1`, branch `review/m1-mod8-13`
- Base commit: **`df72c4a`** (main: Antigravity-verified M1 MUST tier)
- Preconditions to reproduce and paste:
  - working tree clean
  - `uv run --with pytest pytest -q` → **231 passed, 0 failed** (conftest enforces
    Python `>=3.12,<3.14`; the banner must not read 3.11.x — that itself is a finding)
- After any run: `git checkout -- uv.lock` if it shows modified (known pyproject/lock
  drift). Note it; do not treat it as the finding.
- If the commit, the count, or the interpreter differ, **stop and report the mismatch**.

### 2. Read before attacking
- `AGENTS.md` (Universal Rules; rule 10 = no history rewrites)
- `docs/DECISIONS.md` — ADR-001..010
- `docs/MASTER_BUILD_SPEC.md` — §80.5, §83, §98, §110.1, §112, §127.1, §134.1, §134.3
- `project_state.yaml` — NAT ledger, gate state
- Code under review (modules 8–13):
  - `src/jarvis/kernel/effect_envelope.py` (module 8: PREPARE→AUTHORIZE→COMMIT→VERIFY)
  - `src/jarvis/kernel/policy.py` (module 9: four deterministic checks)
  - `src/jarvis/kernel/done_gate.py` + `memory_write.py` (module 10)
  - `src/jarvis/bootstrap.py` + `cli.py` + `kernel/memory_query.py` (module 11)
  - `src/jarvis/observability.py` + observer wiring in event_log/policy/model_gateway (module 12)
  - `tests/acceptance/test_m1_acceptance.py` (module 13: NAT-01..05 + §112)
- Carried M6 fixes now in scope (attack the fixes, not the memory of them):
  - F5 strict version dialect in `registry.py` (`_constraint_matches`, `_NUMERIC_VERSION`)
  - F6 `schema_sha256` binding in `model_gateway.py` + `openai_compatible.py`
  - F14 runtime failover to `fallback_provider_id` on `ProviderTransportError`
  - F8 interpreter gate in `tests/conftest.py`
  - F2/F10 JSON-decode/redirect handling in `providers/openai_compatible.py`
- Verify every file path you cite from disk; do not trust paths quoted in this prompt.

### 3. Attack surfaces — find where these break; don't confirm they exist

**A. Effect envelope (module 8)**
1. Idempotency window: per-key `asyncio.Lock` + `_committed_keys` dict. Attack:
   two different keys racing on the same adapter with side effects; lock dict growth
   (unbounded?); duplicate path returning `model_copy(update={"duplicate": True})` —
   is the frozen model mutated safely? Re-run after engine restart: the in-memory
   committed-keys map is gone — same key re-commits and re-invokes the adapter.
   Real failure or acceptable at M1? Name the concrete consequence.
2. `_refuse` emits `effect.refused` into a throwaway list — the event goes to the log
   but is never attributed to an envelope (no audit_event_ids). Does any downstream
   consumer need the linkage? Is the authorization event chain replayable?
3. AUTHORIZE reads `requested_capabilities` from `intended_change` — attacker-shaped
   input. Prove or break: can any value in `intended_change`/`capability_args` reach
   the adapter or expand the capability set? (NAT-01 zero-effects claims it cannot.)
4. VERIFY is a shallow dict-equality check on postconditions. Construct an adapter
   result where postconditions pass but the effect is semantically wrong. Is that a
   §98 gap or correct M1 scope?

**B. Policy (module 9)**
5. Threshold tables are code, not data. `RISK_MIN_AUTONOMY` maps "moderate"→L3 —
   same as "safe". Spec §59? If a moderate action needs distinct treatment, what
   silently passes today? Cite the spec line either way.
6. `_privacy_violation` iterates manifest contracts; a manifest with ZERO contracts
   + `privacy_class="restricted"` passes (rank check on empty loop). Hard deny or hole?
7. Pure-function claim: identical (manifest, context) → identical decision. The only
   side effect is the `policy.check` event. Verify no hidden ordering/dict-iteration
   nondeterminism leaks into `denials`.

**C. Done-gate + memory write (module 10)**
8. `CompletionGate` gate tables: `CHECKS`/`GATE_REQUIREMENTS` are module data. Can a
   caller construct evidence that satisfies all checks while the task is objectively
   incomplete? What does the gate NOT know that M2 must add?
9. Memory write chain: proposed→verified→committed with `cause_event_id` links. Attack:
   a writer constructed with `principal_id != creator` — what CAN it still emit, and
   does the projection honor it? Authority boundary or none?
10. `MemoryWriter.remember` rejects empty source. Is the rejection event (if any)
    complete, and does the projection digest stay stable after a rejection storm?

**D. Bootstrap + CLI (module 11)**
11. `CoreService.start()` idempotency: second start rebuilds the registry from
    `capability.provider_added` events via `ProviderBinding.model_validate`. Attack:
    an event payload written by an OLD schema version — what happens on replay?
    `extra="forbid"`? Silent drop? Hard crash at boot?
12. `default_home()` reads `JARVIS_HOME` — CLI tests and real runs share the same
    resolution. Can a user-level env var redirect the event log to a path a malicious
    process controls? Severity at M1 vs M2 (secret material lands in payloads).
13. `memory_query.answer` extraction: token-overlap scoring. Try to construct a
    remembered fact that answers the WRONG question with confidence 1.00. This is a
    disclosed extractive path — the finding is about whether confidence 1.00 is honest.

**E. Observability (module 12)**
14. `configure_otel()` default: real spans go where by default? If ConsoleSpanExporter,
    do span attributes ever carry event payload content (secret leak via logs —
    contradicts §112 "secret material never enters durable payloads" by side channel)?
15. Span wiring is optional-everywhere. Prove one production path where a model call
    or event append happens with NO `jarvis.*` span despite §110.1 requiring it.
16. `OtelObserver` + async: `SPAN_MODEL_CALL` wraps an await inside `with` — verify no
    span leaks on cancellation (asyncio.CancelledError through the context manager).

**F. Acceptance suite honesty (module 13)**
17. Read `tests/acceptance/test_m1_acceptance.py` as an adversary: which NAT/§112 test
    would STILL PASS if the underlying module were gutted? (Tests that assert only
    type-identity or non-None are the classic hole.) Name the weakest test.
18. NAT-02 signature half is disclosed-deferred. Does anything in the suite pretend
    the authority check is stronger than the string equality it is?

**G. Cross-cutting**
19. ADR-001 seam after all merges: grep every kernel module for provider-client
    imports (`httpx`, `openai`, `groq`, provider SDKs). `providers/` is the only
    allowed home. Report any violation with file:line.
20. Determinism: `_FixedClock` in acceptance tests vs `SystemClock` in production —
    name one property that passes under the fixed clock but fails under the real one
    (e.g., events sharing identical `created_at_utc` → ordering by timestamp vs seq).

### 4. What good findings look like
Each finding:
- **Severity**: CRITICAL / HIGH / MEDIUM / LOW / NIT
- **Location**: `file:line` (quote the line)
- **Failure mode**: concrete input/state that triggers it
- **Evidence**: minimal reproduction or a proposed test — you MAY add `tests/...`
  files to THIS worktree as evidence; run them (`uv run --with pytest pytest -q
  tests/<file>`) and report the outcome
- **Recommendation**: smallest change that closes it — do not redesign the architecture

Also produce an explicit **no-findings list** for anything you could NOT break.

### 5. Report format (return VERBATIM; no preamble)
```
### Preconditions
<HEAD hash, tree clean, raw pytest summary line(s) reproduced by you, interpreter>

### Findings
<CRITICAL/HIGH/MEDIUM/LOW/NIT — file:line, failure mode, evidence, recommendation>

### No-findings surfaces
<attacked surfaces where nothing broke, one line each>

### Spec/ADR conflicts
<any divergence from an accepted decision, with the exact quote>

### Test proposals
<tests added in this worktree, by path, with their pytest outcome; or "none">
```

Do not merge, rebase, push, or edit `src/`. After runs, `git checkout -- uv.lock`
if modified.