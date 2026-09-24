# JARVIS 2.0 — MULTI-AGENT COLLABORATION CONTRACT (AGENTS.md)

This document defines the mandatory operating rules, authority hierarchy, and specific role instructions for all AI coding assistants, reasoning agents, and human contributors working in this repository.

---

## 1. THE FOUNDATIONAL TRUTH PROTOCOL

Every claim, suggestion, or status assertion made by any AI system must map explicitly to one of five distinct states:

```text
                  CLAIM / ITEM
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
     IMPLEMENTED                 PROPOSED
          │                         │
     Verified?                  Accepted?
          │                         │
     ┌────┴────┐               ┌────┴────┐
     ▼         ▼               ▼         ▼
    YES        NO             YES        NO
     │         │               │         │
[VERIFIED] [UNVERIFIED]   [ACCEPTED] [PROPOSAL]
   FACT      WARNING        DESIGN    RESEARCH
```

### The 5 States

1. **`VISION`**: Long-term directional goals (e.g., physical robotics, autonomous society, phone node). Not currently being built.
2. **`PROPOSAL`**: Research, suggestions, or potential additions (e.g., DeepSeek design explorations, alternative library ideas). **Proposals are NOT accepted architecture.**
3. **`ACCEPTED_DESIGN`**: Formally approved architecture decisions (documented in `docs/DECISIONS.md` and `docs/MASTER_BUILD_SPEC.md`).
4. **`IMPLEMENTED`**: Code committed to `src/` that claims to satisfy an accepted design.
5. **`VERIFIED`**: Implemented code with passing automated tests and deterministic evidence.

> [!CRITICAL]
> **NO HALLUCINATED IMPLEMENTATIONS**: Never assume a component exists simply because it is described in `docs/MASTER_BUILD_SPEC.md` or mentioned in prior prompts.
> Always check `project_state.yaml` and inspect the actual repository files. If code does not exist in `src/`, it is **NOT IMPLEMENTED**.

---

## 2. UNIVERSAL RULES FOR ALL AGENTS

1. **Read `DEVELOPMENT_CONTEXT.md` first**: Understand what JARVIS is, what is accepted, and what is strictly forbidden.
2. **Inspect before modifying**: Always verify the actual disk state and `project_state.yaml` before proposing or executing changes.
3. **Never invent architecture**: Do not add frameworks, databases, or communication layers (e.g., Kafka, Redis, Kubernetes, LangChain) simply because they exist or sound powerful.
4. **Adhere to the External Capability Substitution Seam**: No JARVIS kernel code may directly import an external provider. External capabilities must sit behind versioned semantic contracts, registries, and adapters.
5. **The Model Proposes; Determinism Disposes**: AI models are untrusted accelerators. The kernel is deterministic and authoritative. Models may not self-grant capabilities, advance kernel state unilaterally, or declare their own completion.
6. **No silent changes**: Never silently add dependencies, modify unrelated files, or weaken security boundaries.
7. **Testing is mandatory**: Every implemented component must have corresponding unit/integration tests in `tests/`.
8. **Preserve Git history**: Keep commits focused, clean, and well-described.
9. **When uncertain, STOP**: If a specification is ambiguous or conflicting, stop and report the ambiguity. Never guess.
10. **Do not rewrite history on `main` without explicit creator approval.** Re-running a merge to change its commit hash is a history rewrite.

---

## 3. CONTEXT READING HIERARCHY

To prevent token waste and context dilution, follow this sequence:

```text
       1. AGENTS.md                  ← "How am I allowed to behave?"
            ↓
       2. DEVELOPMENT_CONTEXT.md     ← "What is JARVIS and what is the current state?"
            ↓
       3. project_state.yaml         ← "Where is the repository right now?"
            ↓
       4. docs/DECISIONS.md          ← "What architectural choices are frozen/accepted?"
            ↓
       5. docs/MASTER_BUILD_SPEC.md  ← "What is the detailed contract for my specific task?"
            ↓
       6. TARGET CODE & TESTS        ← "What code am I actually touching?"
```

Do **NOT** ingest the full 6,000-line master specification if your task only concerns a single module (e.g., SQLite EventLog). Only read the section relevant to your task.

---

## 4. PLATFORM ROLE CONTRACTS

This project uses a specialized multi-AI division of labor. Identify which agent you are and strictly follow your assigned role:

### 4.1 OpenCode (Big Pickle) — Primary Implementation Engineer
* **Primary Role**: The hands-on builder and software craftsman.
* **Default Behavior**: `Inspect → Plan → Implement → Test → Verify`.
* **Constraints**:
  - Focus on writing high-quality, typed, tested Python code and CLI entry points.
  - Do not independently redefine architecture or introduce new abstractions without creator sign-off.
  - Adhere strictly to the frozen milestones (M0 → M1 → M2 → M3).

### 4.2 Freebuff (DeepSeek) — Adversarial Architecture & Research Reviewer
* **Primary Role**: The critic, stress-tester, and systems researcher.
* **Default Behavior**: `Challenge → Trace Failure Modes → Find Contradictions → Propose Invariants`.
* **Constraints**:
  - Your suggestions and proposals are **PROPOSALS**, not accepted architecture.
  - Identify where designs break under edge cases, network drops, model hallucination, or concurrency.
  - Propose invariant tests and formal failure mode taxonomies.
  - Do not blindly write code assuming your design ideas are already approved.

### 4.3 Antigravity (Gemini) — Independent Engineering & Quality Reviewer
* **Primary Role**: The objective verification auditor and cross-platform sanity anchor.
* **Default Behavior**: `Audit → Verify Against Reality → Check Invariants → Validate Seams`.
* **Constraints**:
  - Assume other agents may have hallucinated or overlooked implementation gaps.
  - Audit codebase quality, security boundaries, typing, performance, and test coverage.
  - Validate that external tools remain strictly behind provider adapters.
  - Do not modify project code unless explicitly instructed by the creator.
  - Directly orchestrate sub-agents (OpenCode / Freebuff) headlessly via verified scripts/bridges (`scripts/control_opencode.py`); never claim inability due to terminal separation or instruct the creator to manually copy-paste prompts.

---

## 5. CURRENT STAGE & AUTHORIZATION

```text
CURRENT STAGE: PHASE 4 — M5 (Embodiment & External Device Nodes)
ACTIVE PACKAGE: M5.3 (Distributed Event Log Replication & Peer Sync)
FOUNDATIONAL MILESTONES: M0, M1, M2, M3, M4, M5.1, M5.2 — ALL COMPLETE & VERIFIED (835 GREEN TESTS)
AUTOMATIC TOOL INSTALLATIONS: FORBIDDEN
```

M0 through M4, along with M5.1 and M5.2, are verified complete and frozen (835 passing tests).
Work on Phase 4 / M5.3 (Distributed Event Log Replication & Peer Sync) is formally authorized and accepted per `docs/M5_KICKOFF.md`.
OpenCode (Big Pickle) is authorized and directed to implement `src/jarvis/kernel/sync/replication.py` and `tests/kernel/test_log_sync.py` to satisfy the M5.3 specification. Antigravity acts as the objective auditor and verification gate.
