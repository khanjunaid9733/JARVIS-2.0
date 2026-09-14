# JARVIS — MASTER CONTEXT & EXECUTION PROMPT

**Purpose:** This file is the canonical context prompt for continuing the JARVIS project across ChatGPT, DeepSeek, OpenCode, and future engineering agents. It consolidates the project vision, architectural decisions, implementation philosophy, external-tool strategy, current freeze state, and immediate workflow.

**Date context:** 2026-09-14
**Current stage:** M0 machine/environment audit → M1 implementation gate
**Architecture status:** FROZEN for M1 unless real implementation evidence forces a change.

---

## 1. WHO/WHAT WE ARE BUILDING

We are building **J.A.R.V.I.S.**, a personal AI operating system/companion inspired by the fictional JARVIS concept, but implemented as a real engineering system.

The long-term objective is not merely a chatbot, coding agent, voice assistant, or collection of agents. JARVIS should become a persistent, general-purpose cognitive and execution system that can operate across:

- laptop/desktop
- phone
- internet and web services
- files and software
- development environments
- voice and text
- camera/vision
- multiple AI models
- many concurrent specialized agents
- robotics and physical devices
- ROS2/Gazebo and future digital-twin environments
- engineering tools such as MATLAB/Simulink, CAD, PCB/EDA, Arduino/ESP32, etc.

The system should feel like **one continuing identity** even when its models, processes, devices, or execution workers change.

The model is an accelerator inside JARVIS. **The model is not JARVIS itself.**

---

## 2. LONG-TERM COGNITIVE VISION

JARVIS should eventually have:

- persistent identity
- persistent memory
- world model
- self model
- organization/agent model
- goals and priorities
- attention management
- planning and reasoning
- metacognition
- uncertainty and belief management
- causal reasoning
- temporal intelligence
- simulation/prediction
- perception
- learning and self-improvement
- proactive/event-driven behavior
- social/agent cognition
- resource awareness
- model/provider routing
- multimodal interaction
- safe autonomous execution

It should be able to dynamically create, supervise, coordinate, evaluate, replace, stop, and evolve specialized subagents.

A future agent is not merely a prompt plus an LLM call. It is a persistent or ephemeral computational entity with:

- identity
- state
- memory
- perception
- goals
- environment
- feedback
- capabilities
- resource limits
- provenance
- lifecycle

Conceptual lifecycle:

`BORN → UNDERSTAND → PERCEIVE → PLAN → ACT → OBSERVE → REFLECT → COMMUNICATE → COMPLETE/FAIL → DIE/PERSIST/EVOLVE`

Eventually JARVIS may support an agent society containing persistent/project/task/ephemeral agents, teams, reputation/trust, communication protocols, shared workspaces, resource economics, authority, governance, and adaptive topology.

Do NOT attempt to build the full future vision in M1. The architecture must allow it without prematurely implementing it.

---

## 3. CORE ENGINEERING PHILOSOPHY

### 3.1 Event-sourced canonical state

JARVIS uses an **Event-Sourced Cognitive Kernel**.

The event log is the source of truth. Projections are rebuildable.

Conceptual shape:

```text
Event Log → Executive Loop → Effect System
     |             |              |
     |         Model Gateway   Capability Kernel
     \____________________________/
                    |
       Projections: world / memory / missions /
       agents / audit / organization / etc.
```

### 3.2 Deterministic kernel, probabilistic models

Models are powerful but untrusted.

Models may:

- reason
- interpret
- classify
- predict
- generate
- plan
- simulate
- propose
- critique
- summarize
- learn patterns

Models may NOT unilaterally:

- authorize themselves
- grant capabilities
- advance kernel state
- declare completion
- rewrite history
- disable safety controls
- change creator authority
- bypass the effect system

**The model proposes. Determinism disposes.**

### 3.3 Effect mediation

All meaningful external effects pass through JARVIS-controlled mechanisms.

For irreversible/high-risk effects use:

`PREPARE → AUTHORIZE → COMMIT → VERIFY → RECONCILE`

Use idempotency, provenance, typed failures, retries where safe, and deterministic recovery.

---

## 4. INTENT → MANIFEST → CAPABILITY → EFFECT

Intent is the semantic security boundary.

Manifest is the declared execution contract.

Capability is the mechanical authorization boundary.

Effect is the actual external operation.

```text
MODEL / AGENT
      ↓
STRUCTURED INTENT
      ↓
INTENT VALIDATION
      ↓
MANIFEST SYNTHESIS
      ↓
MINIMUM CAPABILITY SET
      ↓
AGENT CAPSULE
      ↓
LOW-LEVEL EFFECTS
```

An intent never executes directly.

The model may propose semantic capability contracts, but it must never select a provider, grant a capability, or bypass validation.

Manifest synthesis:

```text
INTENT
  ↓
CONTRACT PROPOSAL       ← schema-constrained model
  ↓
STATIC VALIDATION       ← deterministic
  ↓
POLICY VIABILITY        ← deterministic
  ↓
MANIFEST                ← frozen + logged
  ↓
CAPABILITY RESOLUTION   ← registry, never model
```

Static validation checks at minimum:

- contract exists
- version constraint resolves to a live provider
- arguments validate against schema
- dependency graph is a DAG
- no undeclared capability is introduced

Policy viability checks at minimum:

- capability grantability
- mission/creator budget
- autonomy/risk level
- privacy/trust compatibility

Failure produces `intent.rejected` with typed failure information.

---

## 5. AGENT CAPSULE

Every agent/process eventually executes in a scoped capsule containing:

- stable principal identity
- manifest
- capability grants
- filesystem scope
- network scope
- process scope
- secret references
- resource budget
- time limit
- environment variables
- artifact workspace
- audit context
- isolation level

A capsule may eventually map to an async task, subprocess, container, VM, TEE, remote worker, GPU worker, or robotics compute node.

---

## 6. EXTERNAL CAPABILITY SUBSTITUTION SEAM

This is an **ARCHITECTURE INVARIANT**.

No JARVIS kernel code directly imports an external provider.

All external capabilities use:

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

Models use the same principle:

```text
MODEL ROLE CONTRACT
     ↓
MODEL REGISTRY
     ↓
MODEL ADAPTER
     ↓
MODEL PROVIDER / SERVING BACKEND
```

The registry is a projection over capability events, not an arbitrary mutable configuration file.

Provider metadata should eventually include:

- provider/repository
- pinned version/commit
- license
- adapter
- trust level
- process model
- network requirements
- health
- metrics
- CVE/security state
- audit date
- fallback provider

Important events include:

- `capability.registered`
- `capability.provider_added`
- `capability.provider_promoted`
- `capability.provider_deprecated`
- `capability.provider_revoked`
- `capability.provider_health_changed`
- `capability.resolved`

External providers should execute outside the canonical kernel process.

---

## 7. THREE FROZEN ARCHITECTURE DECISIONS

### Decision 1 — Manifest synthesis is model-proposed, determinism-disposed

Status: **ACCEPTED / ARCHITECTURE INVARIANT**

The model proposes contracts. It does not choose providers, grant capabilities, or bypass deterministic validation.

### Decision 2 — Provider registration requires creator authority

Status: **ACCEPTED / ARCHITECTURE INVARIANT**

Only the creator principal may emit `capability.provider_added`.

Agents may propose providers, but cannot self-register or self-grant.

The creator keypair is the registry trust anchor.

### Decision 3 — Capability contracts are lower bounds, not equivalences

Status: **ACCEPTED / ARCHITECTURE INVARIANT**

A contract specifies minimum guarantees. Provider adapters publish behavioral profiles.

Substitution succeeds only when:

- the contract/version matches
- the adapter profile satisfies the contract lower bound
- caller strict requirements are satisfied
- golden tasks pass
- upstream mission/FSM/policy logic remains unchanged

No silent downgrade.

If degraded behavior is accepted, it must be visible in provenance.

---

## 8. PROVIDER REGISTRY BOOTSTRAP

The first-run system uses a curated seed registry.

`jarvis init` will seed four initial providers:

1. filesystem
2. terminal
3. one local model adapter
4. HTTP client

The creator is initially the sole authority for:

- REGISTER_PROVIDER
- PROMOTE_PROVIDER
- REVOKE_PROVIDER
- GRANT_CAPABILITY

Agents can propose providers but cannot emit the authoritative registration event.

No self-registration and no self-granting.

---

## 9. MODEL FABRIC

The model layer is provider-agnostic.

JARVIS owns:

- model role contracts
- routing policy
- budgets
- provenance
- lifecycle
- fallback policy
- model selection constraints
- identity continuity

LiteLLM is an implementation component behind the JARVIS Model Gateway. It is NOT the owner of JARVIS routing policy.

vLLM is a model-serving backend, not the model gateway.

Structured output/constrained decoding is a first-class model capability/role. Candidate mechanisms may include native backend constrained decoding, Outlines/equivalent, or Pydantic/Instructor-style adapters, but these remain replaceable implementation choices.

Model replacement must not change JARVIS identity.

---

## 10. MEMORY

Memory is not simply a vector database.

Canonical memory/state belongs to the JARVIS memory/event architecture.

Retrieval systems such as Qdrant may later serve as indexes behind the Memory API, but they are NOT canonical memory.

Memory requires:

- typed memory
- provenance
- source references
- verification
- write policy
- privacy/PII handling
- retrieval
- confidence
- semantic checkpoints
- replay/reconstruction compatibility

---

## 11. WORLD / SELF / ORGANIZATION MODELS

JARVIS eventually maintains three related but distinct models:

### WORLD MODEL
What JARVIS believes about the external world.

### SELF MODEL
What JARVIS believes about its own capabilities, state, limitations, history, uncertainty, and current execution condition.

### ORGANIZATION MODEL
What JARVIS believes about agents, teams, authorities, responsibilities, trust, resources, and relationships within its own computational society.

Do not collapse these into one vague memory database.

---

## 12. PERCEPTION AND MULTIMODALITY

Future perception pipeline:

`RAW INPUT → PERCEIVER → TYPED OBSERVATION → EVENT → WORLD MODEL → CONTEXT ENGINE`

Inputs may eventually include:

- text
- speech
- audio
- camera/video
- screen
- files
- web
- sensors
- robotics telemetry

Perception produces structured observations rather than directly mutating canonical state.

---

## 13. VOICE / PHONE / CONTINUITY

The phone is not a separate assistant.

It is another interface/body/node of the same JARVIS identity.

Eventually JARVIS should be reachable from phone and laptop while maintaining one identity, memory, world model, goals, and event history.

“Always alive” means JARVIS remains operational until explicitly put to sleep/shutdown. A laptop that is powered off cannot execute local processes; therefore true future continuity requires an always-on node, home server/cloud/remote host, and eventually failover.

Do not pretend this problem is solved by keeping a process alive on a laptop.

---

## 14. ROBOTICS FUTURE

Robotics is a later layer, not an M1 dependency.

Desired hierarchy:

```text
JARVIS Executive
      ↓
Robot Mission Planner
      ↓
VLA / VLN / learned perception-planning
      ↓
ROS2
      ↓
Deterministic Controller
      ↓
Hardware
```

Gazebo/digital twins can be used for simulation.

Physical systems require an independent hardware-level emergency stop that JARVIS cannot disable.

---

## 15. OBSERVABILITY

OpenTelemetry is the observability substrate, not the canonical event log.

Required span names include:

- `jarvis.event`
- `jarvis.model.call`
- `jarvis.effect.{name}`
- `jarvis.verify.{name}`
- `jarvis.policy.check`
- `jarvis.registry.resolve`

Every span should carry, where applicable:

- event.id
- principal.id
- mission.id
- task.id

Additional model/effect/policy/registry attributes must follow the project's OBSERVABILITY conventions.

Langfuse/Evidently are subscribers/evaluation tools, not critical-path kernel dependencies.

---

## 16. TESTING / REPLAY / VERIFICATION

The system must prioritize:

- deterministic replay
- property invariants
- event integrity
- schema validation
- idempotency
- restart recovery
- provenance
- effect verification
- golden trajectories
- fault injection
- model/provider replacement tests
- security/capability boundary tests

A model saying “done” is never sufficient evidence of completion.

Completion is established by deterministic kernel state plus verification evidence.

---

## 17. TECHNOLOGY BASELINE FOR M1

Current intended baseline:

- Python 3.12 target
- FastAPI
- Pydantic v2
- SQLite WAL for development
- PostgreSQL later when justified
- asyncio/in-process queues initially
- NATS JetStream later if needed
- Ollama/local model adapter
- OpenAI-compatible model adapter boundary
- OpenTelemetry
- pytest
- pytest-asyncio
- `uv run jarvis`
- systemd / Docker Compose later

Do NOT introduce Kafka, Redis, Kubernetes, graph databases, vector databases, or a heavyweight agent framework on day one merely because they exist.

Use the simplest architecture that satisfies the frozen contracts.

---

## 18. EXTERNAL REPOSITORIES ALREADY EVALUATED

These repositories were reviewed as potential future components:

### High-value / likely integration candidates

- vLLM — model serving
- LiteLLM — provider/API routing implementation behind Model Gateway
- MCP servers — external capability adapters
- Browser Use — browser automation capability provider
- Docling — document parsing/extraction
- Ragas — RAG/final-answer evaluation
- Langfuse — observability/tracing subscriber
- Evidently — evaluation/monitoring
- Pipecat — realtime media/voice pipeline
- Ultralytics — vision; license must be reviewed before distribution
- Open-SWE — coding workforce/reference/integration candidate

### Later / conditional

- Qdrant — retrieval index, not canonical memory
- GraphRAG — retrieval/extraction, not world model
- Qodo PR-Agent — code review/verification

### Research/reference only for now

- LangGraph 101
- ElizaOS
- Feast — only when multiple learned models genuinely share feature infrastructure
- Unsloth — later model training/fine-tuning
- Text-to-SQL agent — specialized skill

Never allow an external repository to become an implicit architectural dependency of the kernel.

Every integration goes through the capability/model substitution seam.

---

## 19. DEVELOPMENT PHASES

### M0 — MACHINE / ENVIRONMENT AUDIT

No building.

Audit the actual laptop/environment and determine whether M1 can be implemented.

Output:

`docs/M0_AUDIT.md`

The audit must record:

- UTC date
- master spec path
- spec version
- Git commit or SHA-256 of audited spec
- requirement statuses
- concise evidence
- exact fix commands for INSTALL_REQUIRED/CONFIG_REQUIRED, without running them

No raw terminal dumps.

### M1 — COGNITIVE KERNEL FOUNDATION

Initial target:

- Event Kernel
- Identity
- deterministic FSM
- Intent ABI
- Capability Contract
- Capability Registry
- Provider Adapter Interface
- Model Gateway
- OpenTelemetry
- structured output validation
- first local model adapter
- first simple capability adapter
- creator authority/bootstrap
- deterministic replay
- tests/invariants

### M2 — MEMORY OS

- typed memory
- PII seam
- embeddings/retrieval
- memory verification
- semantic checkpoints

### M3 — MISSION RUNTIME

- mission runtime
- Saga/effect recovery
- self-healing
- agent capsules
- browser/document/coding adapters
- golden trajectory evaluation

### M4+

- phone
- voice
- vision
- multimodal continuity
- dynamic multi-agent society
- A2A/inter-agent communication

### M5+

- robotics
- VLA/VLN
- ROS2
- Gazebo
- digital twin
- physical device integration

### Future / evidence-driven only

- learned topology
- SNNs
- TEE integration
- durable execution systems
- learned resource allocation
- blockchain
- large-scale distributed infrastructure

These are not to be added merely for sophistication.

---

## 20. M0 → M1 GATE

M1-critical fail conditions:

| Requirement | Fail if |
|---|---|
| Python | <3.11 or >3.13 |
| uv | missing |
| SQLite | WAL unsupported |
| pytest | unavailable/uninstallable |
| pytest-asyncio | unavailable/uninstallable |
| Git | missing or repo uninitialized |
| Local model | Ollama/local adapter unreachable |
| Model inventory | no local model available |
| Repository | not writable |
| Specification | missing from expected path |
| Disk | <10 GB free |

Non-critical for M1; UNKNOWN is acceptable:

- GPU
- CUDA
- Docker
- Node
- Rust
- Go
- ROS2
- Gazebo
- MATLAB
- Simulink
- robotics tools
- engineering software

Verdict rules:

`M1_BUILDABLE_NOW`
→ all M1-critical requirements READY.

`M1_BUILDABLE_AFTER_SETUP`
→ one or more M1-critical requirements are INSTALL_REQUIRED or CONFIG_REQUIRED, with no BLOCKED.

`M1_BLOCKED`
→ any M1-critical BLOCKED OR more than two M1-critical UNKNOWN.

A spec-vs-reality mismatch is reported as a mismatch. Do not silently edit architecture to make the audit pass.

---

## 21. M1 ACCEPTANCE TEST

The intended M1 smoke test is conceptually:

```text
$ jarvis init
  creator keypair created (fingerprint: …)
  event log initialized at ~/.jarvis/log.db
  projections initialized
  registry seeded (4 providers)
  core service started
  pairing code: XXXX-XXXX

$ jarvis say "remember: the safe word is umbrella"
  [thinking]
  memory.write.proposed
  memory.write.verified
  memory.write.committed

$ ^C

$ jarvis
  replayed N events
  projections rebuilt
  identity recovered
  last mission: none
  active agents: 0

$ jarvis say "what is the safe word?"
  umbrella
  (confidence 0.94, source: session 1)

$ jarvis explain <last_event_id>
  cause chain: …
  state transitions: …
  model: local/llama3.2@… , prompt: executive.v1
  retrieved memories: 1 (score 0.91)
  capability checks: …
  no effects outside manifest
  budget: 812 tokens of 20000
```

M1 is not complete if the acceptance test, replay equivalence, restart idempotency, property invariants, or registry constraints fail.

---

## 22. DOCUMENT GOVERNANCE / FREEZE

After M1, manually maintained documentation should be minimized to:

- `MASTER_BUILD_SPEC.md`
- `DECISIONS.md`
- `OBSERVABILITY.md`

Other documentation should preferably be generated from code, schemas, or tooling.

After the M1 freeze:

- do not add architecture merely because an idea sounds useful
- fill genuine gaps in existing sections
- require implementation evidence for architectural changes
- cite code, failure, benchmark, or measured result for significant changes
- mark speculative material for removal

Architecture is changed by evidence, not enthusiasm.

---

## 23. KERNEL CONSTITUTION

The kernel must:

1. own canonical state
2. own identity/lifecycle
3. own intent mediation
4. own policy enforcement
5. own capability authorization
6. treat model output as untrusted proposals
7. mediate every external effect
8. preserve causal provenance
9. make recovery deterministic wherever possible
10. never silently rewrite history
11. never grant capabilities implicitly
12. never allow an agent to declare its own completion
13. never allow an agent to disable its own safety boundary
14. detect runaway computation and coordination
15. preserve continuity across process/model failure
16. permit model/provider replacement without identity loss
17. keep creator authority distinct from learned preference
18. maintain an independent physical emergency-stop path
19. make autonomous behavior auditable
20. make behavior replayable

These are architectural constraints, not optional suggestions.

---

## 24. SECURITY PRINCIPLES

- least privilege
- explicit capabilities
- creator authority separation
- provider isolation
- no implicit grants
- no model-controlled privilege escalation
- provenance on all effects
- secrets referenced, not exposed in prompts/logs
- deterministic authorization
- typed failure taxonomy
- independent physical safety controls
- auditable autonomous behavior
- no silent degradation

External tools are untrusted execution surfaces.

---

## 25. HOW AI AGENTS SHOULD WORK ON THIS PROJECT

When an AI agent receives this context:

1. Treat the frozen master specification as the architectural source of truth.
2. Do not reinvent the architecture.
3. Do not add components just because they are popular.
4. Prefer existing contracts and seams.
5. Keep providers replaceable.
6. Keep canonical state in the kernel/event system.
7. Treat model output as untrusted.
8. Make deterministic mechanisms authoritative.
9. Produce executable artifacts, tests, schemas, migrations, or documentation when requested.
10. Before changing architecture, demonstrate the concrete failure/evidence requiring the change.
11. Preserve backward compatibility where practical.
12. Never silently weaken security or capability boundaries.
13. Never claim something was executed or verified if it was not actually executed or verified.
14. Clearly distinguish FACT, OBSERVATION, HYPOTHESIS, and PROPOSAL.
15. When uncertain, inspect the repository/code/spec before guessing.

---

## 26. CURRENT IMMEDIATE WORKFLOW

The architecture work is currently paused.

The next artifact is:

`docs/M0_AUDIT.md`

OpenCode must perform the M0 machine/environment audit on the user's actual laptop.

Do NOT run `jarvis init` until the environment/repository audit establishes M1 readiness.

Once `docs/M0_AUDIT.md` exists, return it for independent M1 gate evaluation.

The evaluator must not redesign the architecture while evaluating the audit.

The evaluator must return exactly one verdict:

- `M1_BUILDABLE_NOW`
- `M1_BUILDABLE_AFTER_SETUP`
- `M1_BLOCKED`

plus the minimum setup list when applicable.

---

## 27. IMPORTANT CONTEXT ABOUT THE MULTI-AI WORKFLOW

This project has been developed through collaboration between **ChatGPT and DeepSeek**, with **OpenCode** acting as the local engineering/execution environment.

Roles:

```text
CHATGPT / DEEPSEEK
    ↓
architecture / critique / synthesis / specification
    ↓
MASTER SPEC + DECISIONS
    ↓
OPENCODE
    ↓
actual repository inspection / implementation / testing
    ↓
ARTIFACTS + EVIDENCE
    ↓
CHATGPT / DEEPSEEK
    ↓
independent review / gate / next decision
```

Do not assume that a model conversation equals execution evidence.

The actual machine, repository, tests, logs, and artifacts are the source of truth for implementation state.

---

## 28. FINAL INSTRUCTION TO THE NEXT AI

You are contributing to an ambitious long-term JARVIS system, but **do not jump to the final vision**.

Build the foundation correctly.

Respect the frozen architecture.

Use deterministic kernel mechanisms to control probabilistic intelligence.

Keep every external provider replaceable.

Keep identity/state independent of any individual model.

Keep effects mediated, authorized, verified, and auditable.

Do not confuse complexity with intelligence.

Do not confuse an LLM with an agent.

Do not confuse a vector database with memory.

Do not confuse an agent framework with an operating system.

Do not confuse a running process with continuity.

Do not add architecture without evidence.

**The immediate objective is M0 audit → M1 gate → M1 foundation.**

Everything beyond that is deliberately staged.
