# J.A.R.V.I.S. — MASTER BUILD SPECIFICATION
## Persistent Autonomous Cognitive Operating System
### Build driver: OpenCode CLI
### Primary initial builder/analyst: Big Pickle (OpenCode)
### Design principle: open-source/local-first, provider-agnostic, persistent, multimodal, distributed, extensible

> This file is the **master engineering contract** for the JARVIS project.
> OpenCode CLI on the development PC is the primary construction and maintenance environment.
> Big Pickle is the first engineering/reasoning worker used through OpenCode.
> The runtime being built is JARVIS itself; OpenCode is not JARVIS.
>
> **SPEC_VERSION: 1.0.0-freeze** · **Frozen (UTC): 2026-09-14T15:38Z** · **Supersedes:** `_archive/` specification sources
> Post-M1, manually maintained documentation is minimized to this file, `DECISIONS.md`, and `OBSERVABILITY.md`.
> Changes to ACCEPTED decisions require creator approval backed by implementation evidence (see `docs/DECISIONS.md`).
>
> This document must be treated as a living specification. Before changing architecture,
> the builder must read this file, inspect the repository, identify current implementation
> status, update the design artifacts, and then implement incrementally.

---

# 0. MISSION

Build J.A.R.V.I.S. as a persistent personal cognitive operating system for its Creator.

JARVIS is NOT:
- a single LLM
- a chatbot wrapper
- a fixed list of hard-coded agents
- a collection of API calls
- a single OpenCode session

JARVIS IS:
- a persistent identity
- an executive intelligence
- a multimodal perception system
- a memory and knowledge system
- a world/self/creator model
- a planning and decision system
- a dynamic agent factory
- a multi-agent society runtime
- a capability/skill/tool fabric
- a distributed event-driven system
- a computer and internet operator
- eventually a physical/robotic intelligence
- a continuously evaluated and improving system

The long-term objective is a JARVIS instance that remains continuously available across:
- development PC/laptop
- phone
- home/network devices
- remote server/cloud/edge hardware
- robots and other physical devices

The user should be able to talk to the same JARVIS identity from phone and PC and observe/control the same live state.

---

# 1. NON-NEGOTIABLE ARCHITECTURAL PRINCIPLES

## 1.1 Separate the MODEL from the ORGANISM

A model is a reasoning substrate.

An agent is:
MODEL + STATE + MEMORY + GOAL + TOOLS + PERCEPTION + ENVIRONMENT + LOOP + IDENTITY.

JARVIS is:
EXECUTIVE INTELLIGENCE + PERSISTENT STATE + WORLD MODEL + AGENT RUNTIME + CAPABILITY FABRIC + EMBODIMENT.

Therefore no model provider is allowed to become the architectural definition of JARVIS.

## 1.2 Separate OpenCode from JARVIS

OpenCode is the engineering harness used to build and maintain the project.

The target runtime must be able to operate without an OpenCode TUI session remaining open.

OpenCode should be treated as:
- builder
- code-agent interface
- development orchestrator
- debugging environment
- bootstrap mechanism
- optional maintenance operator

JARVIS itself must have its own runtime, services, state, APIs, event loop, memory, identity, and interfaces.

## 1.3 Persistent identity

A single logical JARVIS identity must persist across devices and restarts.

The body/interface may change:
- phone
- PC
- browser
- server
- robot

The identity, memory, permissions, goals, world state, and active missions must remain coherent.

## 1.4 Event-driven operation

JARVIS must not require a user message to do all work.

Supported event sources should eventually include:
- timers
- schedules
- file changes
- Git events
- application events
- system health
- sensor events
- robot telemetry
- agent events
- messages
- webhooks
- external APIs
- notifications

## 1.5 Local-first and free/open-source first

Default priorities:
1. open-source software
2. locally executable models
3. self-hosted services
4. free/public model endpoints when available
5. paid proprietary providers only when they materially improve capability and the user intentionally enables them

Never hard-code the architecture around a paid provider.

Do not assume any free model/service is permanently free. Provider availability is external and may change.

## 1.6 Provider/model agnosticism

Every model call must go through an abstraction such as:

MODEL GATEWAY
  -> provider adapters
  -> model registry
  -> capability metadata
  -> routing
  -> budget/latency policy
  -> failover

Potential model classes:
- large reasoning models
- coding models
- small local models
- vision models
- speech recognition
- speech synthesis
- embedding models
- rerankers
- robotics/perception models
- specialized domain models

The implementation must not assume one specific vendor.

## 1.7 Safety as engineering reliability

Security, permissions, isolation, authorization, auditability, recovery, and human approval are architectural reliability features.

Do not implement blind unrestricted autonomy.

High-impact or irreversible operations must have explicit policy gates.

---

# 2. REALITY CONSTRAINT: "ALWAYS ALIVE"

The user wants JARVIS alive until explicitly put to sleep/shutdown.

This requires an always-on runtime host.

## 2.1 Important distinction

If the laptop is:
- powered on
- connected
- running the JARVIS runtime

then the laptop can host JARVIS.

If the laptop is:
- powered off
- fully asleep
- disconnected
- crashed

then software on that laptop cannot remain alive.

Therefore the architecture MUST support an always-on host option.

## 2.2 Target deployment

Preferred progression:

STAGE A:
PC/laptop runs the entire local stack.

STAGE B:
PC + phone, with phone as remote client.

STAGE C:
PC + phone + home server/NAS/mini-PC.

STAGE D:
hybrid distributed JARVIS:
local PC + always-on home server + optional cloud/remote node.

STAGE E:
fault-tolerant multi-node JARVIS.

The phone should remain usable when the user is away from the PC by connecting to the currently active JARVIS host.

If the PC is off, the system must fail over to another configured node if one exists.

---

# 3. MULTI-BODY / MULTI-DEVICE ARCHITECTURE

Logical topology:

YOU
  |
  v
JARVIS IDENTITY
  |
  +---- PHONE CLIENT
  |
  +---- PC CLIENT/TERMINAL
  |
  +---- WEB CLIENT
  |
  +---- DESKTOP CLIENT
  |
  +---- SERVER NODE
  |
  +---- ROBOT BODY
  |
  +---- EDGE DEVICES

All interfaces must communicate with the same logical JARVIS runtime.

## 3.1 Phone requirements

The phone interface must eventually support:
- voice input
- text input
- live responses
- push notifications
- active task status
- agent status
- mission dashboards
- approvals
- emergency stop/shutdown
- files/artifacts
- camera input
- microphone input
- location only when explicitly enabled
- robot telemetry
- system health
- remote command execution through JARVIS policies

The phone is a CLIENT/BODY, not the canonical source of truth.

## 3.2 PC requirements

The PC is initially:
- development workstation
- high-compute node
- local tool host
- robotics/simulation host
- repository host
- OpenCode build environment

---

# 4. NETWORK / REMOTE ACCESS

Remote access must be private and authenticated.

Preferred architecture:
- private overlay network such as a VPN/mesh VPN
- TLS
- device identity
- authenticated sessions
- per-device permissions
- no unauthenticated raw port exposure

The phone must be able to reach the active JARVIS node when the user is away from home.

The design must support LAN first and remote access second.

---

# 5. JARVIS CORE

Create a central logical service:

jarvis-core

Responsibilities:
- identity
- session coordination
- executive loop
- world state coordination
- goal management
- mission management
- policy enforcement
- model routing
- agent orchestration
- event handling
- high-level decision making

The core must NOT contain every implementation detail.

Use explicit subsystem interfaces.

---

# 6. JARVIS INTERNAL COGNITIVE ARCHITECTURE

## 6.1 Perception

Inputs:
- text
- speech
- images
- video
- screenshots
- files
- terminal output
- web data
- APIs
- system telemetry
- robot sensors
- device sensors

Pipeline:

RAW INPUT
 -> PERCEPTION
 -> OBSERVATION
 -> NORMALIZATION
 -> WORLD MODEL UPDATE
 -> ATTENTION

## 6.2 Attention

Attention score inputs:
- creator priority
- urgency
- importance
- novelty
- risk
- deadline
- relevance
- uncertainty
- anomaly level

Possible outcomes:
- ignore
- store
- monitor
- investigate
- notify
- interrupt
- act

## 6.3 Memory

Implement separate conceptual stores:
- working memory
- episodic memory
- semantic memory
- procedural memory
- prospective memory
- spatial memory
- temporal memory
- social memory
- organizational memory
- failure memory
- preference memory
- skill memory

Do not assume a single vector database is equivalent to memory.

Memory services should support:
- retrieval
- ranking
- updates
- conflict handling
- decay
- importance scoring
- consolidation
- provenance
- forgetting/deletion policies
- backup/export

## 6.4 Belief system

Represent important beliefs with:
- claim
- source
- timestamp
- confidence
- freshness
- evidence
- contradictions
- provenance
- status

Statuses:
- known
- probable
- uncertain
- conflicting
- unverified
- stale
- experimental

## 6.5 Metacognition

JARVIS must represent:
- what it thinks it knows
- what it does not know
- confidence
- uncertainty
- assumptions
- unresolved questions
- verification needs
- previous failures

## 6.6 Self model

JARVIS must know:
- identity
- capabilities
- limitations
- active agents
- active models
- available tools
- connected devices
- health
- resource state
- active commitments
- current focus
- unresolved failures

---

# 7. WORLD MODEL

Create a structured world model / digital twin layer.

Entities:
- creator
- people
- agents
- teams
- projects
- missions
- tasks
- devices
- software
- repositories
- files
- services
- networks
- locations
- robots
- sensors
- actuators
- experiments
- artifacts
- resources
- events

Relationships:
- owns
- contains
- depends_on
- connected_to
- controls
- created_by
- assigned_to
- uses
- caused
- observed
- verified_by
- derived_from
- supersedes

The world model should expose current state plus history.

---

# 8. CREATOR MODEL

JARVIS should maintain an explicit representation of Creator preferences and intent.

Store:
- preferences
- project priorities
- recurring habits
- technical direction
- communication preferences
- active goals
- long-term objectives
- explicit rules
- permissions
- device ownership
- trusted devices/agents

Do not infer sensitive personal facts unnecessarily.

Creator profile data must be user-controlled and exportable/deletable.

---

# 9. GOAL / MISSION SYSTEM

Hierarchy:

Creator Intent
 -> Strategic Goal
 -> Project Goal
 -> Mission
 -> Objective
 -> Task
 -> Action

Each goal should include:
- owner
- priority
- deadline
- status
- constraints
- dependencies
- success criteria
- verification criteria
- budget
- risk level

JARVIS must support:
- goal creation
- prioritization
- conflict resolution
- pause
- resume
- abandon
- revise
- delegate
- complete
- verify

---

# 10. PLANNING SYSTEM

Support:
- decomposition
- hierarchical planning
- search
- scheduling
- optimization
- contingency plans
- replanning
- partial-order planning where useful
- resource-aware planning
- deadline-aware planning

Planning output should be structured, not only natural language.

---

# 11. DECISION SYSTEM

For consequential actions evaluate:
- expected value
- success probability
- confidence
- risk
- cost
- latency
- reversibility
- side effects
- authorization
- resource availability

Possible result:
- execute
- simulate
- verify
- ask Creator
- defer
- reject
- abort

---

# 12. SIMULATION / POSSIBLE-WORLD ENGINE

Before risky or expensive actions, JARVIS should be able to create alternative scenarios.

REAL STATE
 -> WORLD MODEL
 -> SIMULATION(S)
 -> OUTCOME ESTIMATION
 -> DECISION

Software:
- sandbox
- container
- VM
- staging

Robotics:
- Gazebo or equivalent
- digital twin
- physics simulation

General decision making:
- scenario generation
- counterfactual reasoning
- what-if analysis

---

# 13. CAUSAL / EXPERIMENTAL REASONING

Support:

Hypothesis
 -> prediction
 -> experiment
 -> observation
 -> analysis
 -> belief update

Experiments may be:
- software tests
- simulations
- literature studies
- data analysis
- hardware experiments

JARVIS should prefer evidence over unsupported confidence.

---

# 14. AGENT RUNTIME

An agent is a persistent or temporary computational organism.

Required fields:
- agent_id
- parent_id
- identity
- role
- objective
- lifecycle state
- model
- memory references
- tools
- capabilities
- permissions
- resource budget
- environment
- communication endpoint
- health
- performance history

Lifecycle:

BORN
 -> INITIALIZE
 -> UNDERSTAND
 -> PERCEIVE
 -> PLAN
 -> ACT
 -> OBSERVE
 -> VERIFY
 -> REFLECT
 -> LEARN
 -> COMMUNICATE
 -> CONTINUE / COMPLETE / FAIL / RETIRE / RECREATE

Agents must support cancellation and deadlines.

---

# 15. AGENT FACTORY

JARVIS creates agents dynamically based on required capabilities.

Input:
- mission
- constraints
- required skills
- risk
- time
- resources

Output:
- agent specification
- model selection
- permission set
- tools
- memory scope
- expected result
- resource budget
- lifetime

Agent creation must be data-driven, not hard-coded to a tiny fixed set.

---

# 16. AGENT SOCIETY

Hierarchy:

JARVIS
  -> commanders
     -> project agents
        -> specialists
           -> workers
              -> ephemeral workers

Capabilities:
- delegation
- communication
- collaboration
- competition where useful
- conflict resolution
- trust
- reputation
- role assignment
- performance tracking
- promotion
- retirement
- replacement

Do NOT assume every agent is equally trusted.

---

# 17. AGENT COMMUNICATION

Create an internal messaging system.

Message types:
- task_request
- task_response
- event
- observation
- evidence
- warning
- proposal
- vote
- escalation
- cancellation
- heartbeat
- status
- artifact_reference

Each message should include:
- sender
- recipient
- timestamp
- correlation_id
- mission_id
- task_id
- priority
- payload
- provenance

Prefer structured messages over uncontrolled natural-language-only coordination.

---

# 18. SHARED COGNITIVE WORKSPACE

Use:
- message bus
- shared blackboard/workspace
- artifact registry
- state store
- event stream

Agents should exchange references to shared artifacts rather than copying huge contexts unnecessarily.

---

# 19. CAPABILITY GRAPH

Represent capabilities separately from tools.

Tool:
- terminal

Skill:
- debug a Python application

Capability:
- software debugging

Composition:
terminal + Python + Git + tests + code model + reasoning
 -> software debugging capability

JARVIS should be able to discover capability compositions.

---

# 20. SKILL SYSTEM

Skills are reusable executable procedures.

Each skill should have:
- name
- description
- prerequisites
- required tools
- required permissions
- inputs
- outputs
- reliability
- examples
- verification method
- version
- provenance

Skills can be:
- installed
- learned
- composed
- tested
- versioned
- deprecated

---

# 21. MODEL FABRIC

Provide:
- model registry
- model adapter
- routing policy
- local model manager
- cloud model adapter
- fallback
- health check
- latency metrics
- cost metrics

Model routing should depend on:
- task type
- quality required
- privacy
- latency
- token budget
- local hardware
- availability
- tool requirements

---

# 22. MODEL ROLES

Potential model roles:
- executive reasoning
- planning
- coding
- fast classification
- vision
- speech recognition
- speech synthesis
- embedding
- reranking
- robotics perception
- specialist domain reasoning

One model may perform multiple roles.

---

# 23. TOOL FABRIC

Tools may include:
- filesystem
- terminal
- shell
- browser
- web search
- HTTP/API clients
- Git
- GitHub
- databases
- Python
- containers
- SSH
- local applications
- MATLAB/Simulink
- CAD
- PCB tooling
- ROS2
- Gazebo
- serial
- microcontrollers
- cameras
- microphones
- speakers
- robot control interfaces

Do not hard-code every future tool into core logic.

Use a registry/plugin/MCP-style interface.

---

# 24. COMPUTER-USE SYSTEM

Support:
- screen observation
- application discovery
- input automation
- terminal operation
- file manipulation
- browser use
- result verification

Loop:

OBSERVE
 -> PLAN
 -> ACT
 -> OBSERVE
 -> VERIFY

---

# 25. EVENT BUS

All subsystems should be able to publish/subscribe to events.

Examples:
- creator_message
- device_online
- device_offline
- file_changed
- git_commit
- timer_fired
- agent_started
- agent_failed
- agent_completed
- model_unavailable
- robot_alert
- experiment_finished
- system_health_changed

---

# 26. SCHEDULER

Support:
- one-time schedules
- recurring schedules
- deadlines
- delayed execution
- long-running jobs
- wake events
- cancellation
- dependency-aware scheduling

Long-lived intentions should survive process restarts.

---

# 27. RESOURCE ORCHESTRATOR

Track:
- CPU
- GPU
- RAM
- storage
- tokens
- API quotas
- network
- battery
- time
- money
- agent slots
- human attention

Resources should be budgeted per mission/agent.

---

# 28. DISTRIBUTED RUNTIME

Target deployment:

LOCAL:
- PC
- laptop
- edge

REMOTE:
- home server
- NAS
- VPS/cloud
- specialized GPU node

PHYSICAL:
- robot
- microcontroller
- sensors

Required distributed concepts:
- service discovery
- authentication
- heartbeats
- retries
- timeouts
- leases
- cancellation
- queues
- state consistency
- checkpointing
- failover
- offline buffering

---

# 29. DATA / STATE LAYERS

Separate:
- operational state
- event history
- memory
- world model
- artifacts
- configuration
- secrets
- telemetry

Use appropriate storage rather than forcing one database to do everything.

Candidate categories:
- relational database
- object/file storage
- vector index
- graph store
- time-series store
- append-only event log

Choose implementations based on actual requirements during build.

---

# 30. IDENTITY / SECURITY

Every:
- user
- device
- agent
- service
- model gateway
- tool
- execution session

should have a stable identity.

Permissions must be capability-based / least privilege.

Examples:
READ_FILES
WRITE_PROJECT
EXECUTE_SHELL
NETWORK_ACCESS
ACCESS_CAMERA
ACCESS_MIC
CONTROL_ROBOT
DEPLOY_SERVICE
DELETE_DATA

High-impact permissions require stronger policy.

---

# 31. AUTHORIZATION

Every consequential action passes through an authorization layer.

Action
 -> policy evaluation
 -> permission check
 -> risk classification
 -> user approval if required
 -> execution
 -> audit

Irreversible actions should never become silently unrestricted just because the system is in autonomous mode.

---

# 32. AUDIT / PROVENANCE

Every important action should record:
- who/what initiated it
- which agent
- which model
- model version
- prompt/context reference
- tool
- inputs
- outputs
- timestamps
- authorization
- result
- verification
- failures

This must support debugging and replay.

---

# 33. OBSERVABILITY

Build:
- structured logs
- metrics
- traces
- event history
- agent lineage
- resource usage
- model performance
- task performance

Dashboard views:
- current mission
- active agents
- agent health
- system health
- model usage
- resource usage
- pending approvals
- alerts
- recent failures

---

# 34. FAILURE / RECOVERY

Failures are first-class objects.

Store:
- failure type
- origin
- affected task
- affected agent
- evidence
- suspected cause
- recovery options
- retries
- outcome

Recovery:
- retry
- restart
- checkpoint restore
- rollback
- agent replacement
- model fallback
- tool fallback
- degraded mode
- safe shutdown

---

# 35. SELF-HEALTH

JARVIS should continuously monitor itself.

Subsystem health:
- core
- memory
- database
- message bus
- model gateways
- agents
- scheduler
- device connections
- network
- robot interfaces

Use:
- heartbeats
- watchdogs
- health checks
- automatic restart where safe
- escalation where not safe

---

# 36. VERIFICATION ENGINE

For consequential outputs:
- second-pass review
- critic agent
- independent model
- test suite
- simulation
- evidence checking
- physical verification

Pattern:

GENERATE
 -> VERIFY
 -> EXECUTE
 -> OBSERVE
 -> VERIFY RESULT

Avoid using the exact same unchecked inference as both generator and sole verifier for important operations.

---

# 37. EVALUATION ENGINE

Measure:
- task success
- reliability
- calibration
- latency
- cost
- tool success
- memory retrieval quality
- planning quality
- multi-agent coordination
- recovery success
- generalization
- autonomy
- user satisfaction

Create regression benchmarks.

---

# 38. VERSIONING

Version:
- JARVIS core
- agents
- skills
- models/configuration
- prompts/system policies
- memory schemas
- workflows
- tools
- robot software
- deployment artifacts

Support:
- checkpoints
- rollback
- migrations
- canary changes
- staging
- production

---

# 39. SELF-IMPROVEMENT

JARVIS may propose:
- new skill
- new agent type
- new workflow
- new routing policy
- new memory method
- new tool adapter
- optimization
- architectural improvement

Process:

PROPOSE
 -> SANDBOX
 -> TEST
 -> EVALUATE
 -> COMPARE
 -> APPROVE/POLICY GATE
 -> DEPLOY
 -> MONITOR
 -> ROLLBACK IF NECESSARY

Do not let the running production system rewrite itself without tests/versioning.

---

# 40. ROBOTICS / EMBODIMENT

Robotics architecture:

JARVIS
 -> robot executive
 -> mission planner
 -> navigation/planning
 -> controller
 -> real-time system
 -> actuators

Sensors:
- camera
- depth
- LiDAR
- IMU
- encoders
- force
- temperature
- battery/current/voltage
- proximity

Software ecosystem may eventually include:
- ROS2
- Gazebo or another simulator
- OpenCV
- PyTorch
- CUDA
- microcontrollers

General-purpose reasoning models should not directly replace deterministic low-level control loops.

---

# 41. DIGITAL TWIN

Maintain digital representations of important physical systems:
- robot geometry
- sensors
- actuators
- software
- configuration
- state
- history
- maintenance
- calibration
- performance

Real robot <-> digital twin <-> simulation

---

# 42. PHONE AS LIVE JARVIS BODY

Phone architecture:

PHONE
 -> secure connection
 -> JARVIS gateway
 -> JARVIS core
 -> current world/mission state

The app should provide:
- live chat
- voice
- notifications
- streaming status
- agent list
- mission controls
- approval controls
- camera
- microphone
- emergency stop
- sleep/wake command
- system dashboard

The phone should reconnect automatically after network changes.

---

# 43. JARVIS LIFECYCLE

Supported modes:
- RUNNING
- IDLE
- SLEEPING
- MAINTENANCE
- DEGRADED
- EMERGENCY
- SHUTDOWN

SLEEP:
- preserve state
- stop active workloads according to policy
- maintain minimal gateway/identity if configured
- wait for wake trigger

SHUTDOWN:
- explicitly stop the runtime
- save state
- close active work safely
- terminate non-essential agents
- preserve recovery checkpoint

Wake:
- manual phone command
- local command
- configured event
- scheduled wake
- policy-approved external event

---

# 44. "LIVING PARTNER" EXPERIENCE

The user experience should feel persistent and continuous without pretending the system is conscious.

JARVIS should remember:
- ongoing conversations
- open missions
- previous failures
- project context
- pending work
- commitments
- recent world changes

It should be able to say:
- what it is currently working on
- what changed
- what failed
- what needs attention
- what it recommends next

This continuity is created by state, memory, event processing, and long-running execution—not by claiming biological consciousness.

---

# 45. PERSONALITY LAYER

Personality should be replaceable without changing core cognition.

Configurable:
- voice
- formality
- humor
- verbosity
- initiative
- communication style

Identity, security, state, and memory must remain independent of personality configuration.

---

# 46. OPEN-SOURCE / FREE-FIRST TECHNOLOGY POLICY

For every subsystem evaluate in this order:

1. mature open-source local option
2. open-weight self-hosted option
3. free hosted option
4. low-cost hosted option
5. paid proprietary option

The architecture must permit replacement.

Examples of broad technology categories:
- Python/TypeScript/Rust/Go as appropriate
- PostgreSQL or equivalent relational store
- Redis/NATS/Kafka-like event infrastructure where justified
- local vector search
- graph storage where justified
- Docker/containers
- Linux services
- ROS2/Gazebo
- open-source speech/vision models
- open-source UI/mobile frameworks
- VPN/mesh networking

Do not choose a technology merely because it is fashionable.

---

# 47. OPENCODE BUILD CONTRACT

OpenCode is the primary software construction tool.

On every implementation task:

1. Read this MASTER_BUILD_SPEC.md.
2. Inspect the existing repository.
3. Inspect architecture/status docs.
4. Determine what is already implemented.
5. Do not overwrite working systems blindly.
6. Produce/update an implementation plan.
7. Implement the smallest coherent increment.
8. Run tests.
9. Run static checks/lint/type checks where applicable.
10. Verify integration.
11. Update documentation.
12. Record architectural decisions.
13. Report what changed, what was tested, and what remains.

OpenCode should use subagents when useful.

Use specialized roles such as:
- architect
- researcher
- backend engineer
- frontend engineer
- mobile engineer
- agent-runtime engineer
- database engineer
- security engineer
- DevOps engineer
- robotics engineer
- test engineer
- documentation engineer

Do not create agents merely for the appearance of parallelism.

---

# 48. BIG PICKLE BUILD ROLE

Big Pickle is the initial primary reasoning/build model inside OpenCode.

Its mission:
- analyze this specification
- inspect the repo
- find contradictions
- identify missing implementation details
- produce a dependency-aware roadmap
- create the project skeleton
- implement incrementally
- verify with tests
- delegate tasks to subagents where appropriate
- maintain architecture docs
- flag assumptions
- never silently remove required capabilities

Big Pickle must not assume the entire architecture can be built in one prompt.

It should operate as an engineering lead inside OpenCode.

---

# 49. ROOT REPOSITORY DOCUMENTATION

At minimum create:

/JARVIS
  /docs
    MASTER_BUILD_SPEC.md
    ARCHITECTURE.md
    ROADMAP.md
    DECISIONS.md
    SECURITY.md
    THREAT_MODEL.md
    DATA_MODEL.md
    AGENT_MODEL.md
    MEMORY_MODEL.md
    CAPABILITY_MODEL.md
    API_CONTRACTS.md
    DEPLOYMENT.md
    MOBILE.md
    ROBOTICS.md
    TESTING.md
    OBSERVABILITY.md
    CHANGELOG.md

  /apps
    /phone
    /web
    /desktop

  /services
    /jarvis-core
    /gateway
    /agent-runtime
    /memory
    /world-model
    /event-bus
    /scheduler
    /model-gateway
    /tool-runtime
    /security
    /observability
    /evaluation

  /agents
    /templates
    /roles
    /skills

  /packages
    /schemas
    /protocols
    /client-sdk
    /agent-sdk

  /infra
    /docker
    /deployment
    /networking

  /robotics
    /ros2
    /simulation
    /hardware

  /tests
    /unit
    /integration
    /system
    /evaluation

  /scripts

The exact language/framework is to be selected by the implementation analysis, not assumed here.

### 49.1 Document consolidation policy

After M1, manually maintained documents reduce to:

- MASTER_BUILD_SPEC.md
- DECISIONS.md
- OBSERVABILITY.md

All other documents in `/docs` become *generated artifacts*:

| Document | Generated from |
|---|---|
| ARCHITECTURE.md | code structure + module docstrings |
| DATA_MODEL.md | Pydantic schemas |
| API_CONTRACTS.md | FastAPI OpenAPI export |
| AGENT_MODEL.md | agent schema + role registry |
| MEMORY_MODEL.md | memory schemas + retention policies |
| CAPABILITY_MODEL.md | contract registry export |
| TESTING.md | test tree + coverage + golden task manifest |
| ROADMAP.md | milestone YAML |
| CHANGELOG.md | git log + release tags |
| SECURITY.md | policy files + capability matrix |
| THREAT_MODEL.md | manual, reviewed quarterly |
| DEPLOYMENT.md | deployment manifests |
| MOBILE.md | app source + API contracts |
| ROBOTICS.md | ROS2 packages + hardware config |

Any document that is not consumed by tooling is a document that will drift.
Auto-generation is not optional after M1.

---

# 50. DATA CONTRACTS

Use explicit schemas for:
- Agent
- Mission
- Task
- Goal
- Event
- Observation
- Belief
- Memory
- Artifact
- Capability
- Skill
- Tool
- Device
- Resource
- Permission
- Decision
- Action
- VerificationResult
- Failure
- Evaluation
- Model
- Session

Prefer typed/versioned schemas and migrations.

---

# 51. API / EVENT CONTRACT

The phone, web UI, desktop UI, automation services, and agents must communicate through stable contracts.

Core API categories:
- auth
- sessions
- chat
- voice
- missions
- tasks
- agents
- devices
- memory
- world state
- approvals
- tools
- system health
- events
- artifacts

Streaming:
- server-sent events or WebSocket-like live channel as appropriate

---

# 52. SECURITY THREAT MODEL

Threats to consider:
- prompt injection
- malicious files
- compromised tools
- malicious MCP servers
- credential leakage
- agent privilege escalation
- unauthorized remote access
- compromised phone
- malicious agent communication
- poisoned memory
- supply-chain attacks
- model manipulation
- unsafe robotic commands
- data exfiltration
- destructive commands
- runaway agent loops
- resource exhaustion

Mitigations:
- least privilege
- sandboxing
- scoped credentials
- isolated workers
- tool allowlists
- network policy
- input/output validation
- audit logs
- rate limits
- budget limits
- kill/recovery
- independent verification
- secure secret handling

---

# 53. AGENT KILL / CONTAINMENT

JARVIS must be able to:
- pause agent
- revoke tools
- revoke network
- terminate process
- quarantine workspace
- rotate credentials
- preserve forensic state
- recreate clean agent

Kill must be a supported lifecycle operation, not a manual debugging trick.

---

# 54. RESOURCE ECONOMY

Agent execution should account for:
- compute
- memory
- tokens
- latency
- network
- storage
- money
- device availability
- human interruption

Introduce quotas and budgets.

Example:

mission budget
 -> agent budgets
 -> tool budgets
 -> model budgets

---

# 55. AGENT REPUTATION

Record performance:
- completion rate
- verification rate
- error rate
- latency
- resource use
- domain-specific reliability

Use this history in future delegation and verification decisions.

Do not equate reputation with absolute trust.

---

# 56. CONTEXT ENGINE

Do not inject the entire memory into every prompt.

Construct context from:
- current task
- relevant world state
- relevant memories
- relevant artifacts
- relevant policies
- recent events
- available tools
- active agents
- uncertainty
- success criteria

This is a central optimization layer.

---

# 57. KNOWLEDGE / INFORMATION HYGIENE

Tag information as:
- source
- date
- confidence
- freshness
- private/public
- verified/unverified
- experimental
- conflicting

Search and retrieval should prefer fresher and higher-quality evidence.

---

# 58. HUMAN ATTENTION AS A RESOURCE

Do not interrupt the Creator unnecessarily.

JARVIS should batch low-priority events.

Interrupt only when:
- urgent
- important
- deadline-critical
- anomalous
- approval-required
- safety-critical

---

# 59. AUTONOMY LEVELS

Define:

L0 — conversation only
L1 — suggest
L2 — execute after approval
L3 — execute low-risk routine operations
L4 — autonomous missions within explicit boundaries
L5 — distributed autonomous operation with policy oversight

A mission must declare its autonomy level.

---

# 60. BUILD PHASES

## PHASE 0 — REPOSITORY FOUNDATION
- project repository
- docs
- schemas
- configuration
- logging
- test harness
- CI
- local development environment

## PHASE 1 — JARVIS CORE
- identity
- sessions
- event loop
- executive
- model gateway
- basic tools
- command interface

## PHASE 2 — PERSISTENCE
- operational state
- memory service
- checkpoints
- world model foundation
- event history

## PHASE 3 — AGENT RUNTIME
- lifecycle
- agent definitions
- communication
- cancellation
- resource budgets

## PHASE 4 — DYNAMIC AGENT FACTORY
- role generation
- skill mapping
- model routing
- permission assignment
- temporary/persistent agents

## PHASE 5 — AGENT SOCIETY
- teams
- hierarchy
- trust
- reputation
- shared workspace
- governance

## PHASE 6 — CAPABILITY FABRIC
- tool registry
- skill registry
- capability graph
- composition

## PHASE 7 — COMPUTER / INTERNET BODY
- filesystem
- terminal
- browser
- APIs
- Git/GitHub
- computer-use

## PHASE 8 — PHONE BODY
- secure gateway
- mobile UI
- voice
- notifications
- live state
- remote controls

## PHASE 9 — ALWAYS-ON DEPLOYMENT
- system service
- watchdogs
- backup node
- remote access
- failover

## PHASE 10 — LEARNING / EVALUATION
- benchmarks
- memory consolidation
- feedback loops
- evaluation
- regression system

## PHASE 11 — SIMULATION / ROBOTICS
- digital twin
- ROS2
- Gazebo
- perception
- planning
- hardware interface

## PHASE 12 — DISTRIBUTED JARVIS
- multi-node runtime
- edge/cloud
- resource scheduler
- replicated state
- service discovery

## PHASE 13 — SELF-DEVELOPMENT
- improvement proposals
- sandbox testing
- skill generation
- workflow generation
- architecture experiments

---

# 61. IMPLEMENTATION ORDER RULE

Do not attempt Phase 13 before Phase 1-12 foundations are sufficiently reliable.

Every phase should have:
- definition of done
- tests
- failure handling
- documentation
- rollback strategy
- metrics

---

# 62. FIRST BUILD OBJECTIVE

The first job for OpenCode/Big Pickle is NOT "build all of JARVIS."

The first job is:

1. Inspect this specification.
2. Inspect the repository.
3. Propose a concrete architecture.
4. Identify contradictions and missing decisions.
5. Create the documentation tree.
6. Create the initial repo skeleton.
7. Implement Phase 0.
8. Implement the minimal Phase 1 kernel.
9. Add tests.
10. Run and report results.
11. Continue only after the foundation is coherent.

---

# 63. ENGINEERING RULES FOR BIG PICKLE

When uncertain:
- inspect first
- search documentation
- measure current implementation
- prefer reversible changes
- avoid premature complexity
- do not invent APIs
- do not assume providers are free/permanent
- do not leak secrets
- do not expose raw network services unnecessarily
- preserve backwards compatibility where practical
- update docs after architecture changes

When encountering a missing requirement:
- record it in DECISIONS.md
- state the assumption
- choose the least coupling solution
- keep the architecture replaceable

When an implementation is blocked:
- report the blocker
- propose alternatives
- do not fake completion

---

# 64. ACCEPTANCE CRITERIA FOR "JARVIS IS REAL"

JARVIS is considered a genuine early system when all of the following work:

1. Same JARVIS identity survives restart.
2. JARVIS can remember prior interactions.
3. JARVIS can maintain active missions.
4. JARVIS can spawn and manage an agent.
5. Agents have separate identities and permissions.
6. Agents communicate through structured messages.
7. JARVIS can select a model dynamically.
8. JARVIS can use real tools.
9. JARVIS can observe tool results.
10. JARVIS can verify important results.
11. JARVIS can recover from an agent failure.
12. JARVIS can receive asynchronous events.
13. JARVIS can be accessed from the phone.
14. Phone and PC show the same live state.
15. JARVIS can continue when the user is away from the PC if an active remote/always-on node exists.
16. JARVIS can enter sleep and wake states.
17. JARVIS can be shut down cleanly.
18. The system is auditable.
19. The system has automated tests.
20. The system can be upgraded without destroying memory/state.

---

# 65. DEFINITION OF DONE FOR ANY FEATURE

A feature is not done when code compiles.

It is done when:
- implementation exists
- schema/contracts exist
- tests exist
- error cases are handled
- permissions are defined
- observability exists
- documentation is updated
- integration is verified
- rollback/recovery is understood

---

# 66. LONG-TERM NORTH STAR

The ultimate architecture is:

YOU
 |
 v
CREATOR INTERFACE
 |
 v
JARVIS IDENTITY
 |
 +---- COGNITION
 |
 +---- MEMORY
 |
 +---- WORLD MODEL
 |
 +---- SELF MODEL
 |
 +---- EXECUTIVE
 |
 +---- GOALS
 |
 +---- PLANNING
 |
 +---- SIMULATION
 |
 +---- MODEL FABRIC
 |
 +---- AGENT FACTORY
 |
 +---- AGENT SOCIETY
 |
 +---- CAPABILITY FABRIC
 |
 +---- EVENT/SCHEDULING FABRIC
 |
 +---- DISTRIBUTED RUNTIME
 |
 +---- DIGITAL WORLD
 |
 +---- INTERNET
 |
 +---- PHYSICAL WORLD
 |
 +---- ROBOTICS
 |
 +---- LEARNING
 |
 +---- EVALUATION
 |
 +---- SELF-DEVELOPMENT
 |
 +---- MULTI-BODY DEVICE ACCESS
 |
 +---- PHONE + PC + REMOTE NODES

Cross-cutting:
IDENTITY
SECURITY
AUTHORIZATION
PROVENANCE
OBSERVABILITY
RECOVERY
RESOURCE GOVERNANCE
PRIVACY
VERSIONING
EVALUATION

The goal is not to simulate a fictional consciousness.

The goal is to engineer the functional properties that make JARVIS feel like a persistent, capable, context-aware living digital partner:
continuity + memory + perception + initiative + competence + agency + communication + learning + embodiment.

---

# 67. CURRENT STATUS TEMPLATE

OpenCode must maintain this section.

Current phase:
TBD

Completed:
TBD

In progress:
TBD

Blocked:
TBD

Known architectural risks:
TBD

Known technical debt:
TBD

Next milestone:
TBD

Last verified:
TBD

---

# 68. BUILDER COMMANDMENT

DO NOT BUILD A DEMO THAT LOOKS LIKE JARVIS.

BUILD THE INFRASTRUCTURE THAT CAN BECOME JARVIS.

Every shortcut must be evaluated against the long-term architecture.

Every subsystem should be replaceable.

Every important state should be persistent.

Every consequential action should be observable.

Every autonomous capability should be bounded and testable.

Every agent should be disposable.

JARVIS identity and creator state should remain continuous.

---

# 69. INITIAL OPENCODE HANDOFF PROMPT

Use this specification as the source of truth.

You are the lead engineer for the JARVIS project.

Your first task is to deeply inspect the repository and this specification.

Do NOT attempt to implement the entire system at once.

Perform the following sequence:

1. Read MASTER_BUILD_SPEC.md completely.
2. Inspect the repository and current environment.
3. Detect existing code, tools, dependencies, operating system, available runtimes, available GPUs/accelerators, and existing project conventions.
4. Identify requirements that conflict with the current environment.
5. Create ARCHITECTURE.md with the concrete implementation architecture.
6. Create ROADMAP.md with dependency-aware milestones.
7. Create DECISIONS.md with explicit assumptions and unresolved design decisions.
8. Create the project structure.
9. Implement Phase 0.
10. Implement the smallest coherent Phase 1 JARVIS kernel.
11. Add tests and health checks.
12. Run the complete test suite.
13. Report:
   - what was implemented
   - files changed
   - tests run
   - failures
   - assumptions
   - next implementation step

Use OpenCode subagents when parallel work is genuinely useful.
Do not fabricate completion.
Do not silently remove requirements.
Do not hard-code a single vendor.
Keep the system modular so future local/open-source components can replace individual services.

The repository itself is the executable embodiment of this specification.

---


# 71. RESEARCH-GROUNDED COMPLETENESS AUDIT — ADDITIONAL REQUIREMENTS

This section was added after a dedicated review of recent agent-system literature.

The architecture must explicitly include the following capabilities because they are easy to
miss when designing only from software-architecture intuition.

## 71.1 Memory is a controlled write-manage-read process

Memory must NOT be modeled as "save everything to a vector database".

Required memory loop:

PERCEIVE
 -> SELECT WHAT TO WRITE
 -> STORE
 -> ORGANIZE
 -> CONSOLIDATE
 -> RETRIEVE
 -> USE
 -> UPDATE

Memory management must support:
- write filtering
- importance estimation
- salience
- temporal indexing
- semantic indexing
- hierarchical compression
- contradiction detection
- source/provenance tracking
- learned retrieval policies
- forgetting
- privacy/deletion
- multimodal memory
- causal grounding where appropriate

The memory subsystem must measure retrieval quality and downstream decision usefulness.

## 71.2 Agent cognition must be separable from execution

Use a separation such as:

COGNITIVE POLICY / REASONING
        |
        v
STRUCTURED PLAN / INTENT
        |
        v
EXECUTION RUNTIME
        |
        v
TOOLS / ENVIRONMENT

Do not embed irreversible execution directly inside free-form reasoning.

## 71.3 Explicit belief / uncertainty management

JARVIS should not maintain only "answers".

It should maintain hypotheses/beliefs with:
- confidence
- evidence
- uncertainty
- freshness
- contradictions
- assumptions
- source provenance
- verification status

This must feed planning and action selection.

## 71.4 Continual learning without constant model retraining

JARVIS must be able to improve behavior through:
- memory consolidation
- skill acquisition
- policy/routing adaptation
- error-pattern learning
- workflow optimization
- agent reputation
- knowledge updates
- retrieval improvements

Model fine-tuning is optional and must not be required for ordinary long-term learning.

## 71.5 Long-horizon credit assignment

For missions lasting hours/days, maintain:
- mission lineage
- subgoal outcomes
- action-result associations
- failures
- causal hypotheses
- intermediate checkpoints
- lessons learned

JARVIS must be able to answer:
"What earlier decision caused this current state?"

## 71.6 Cognitive load / context economics

Context itself is a managed resource.

The system must optimize:
- context size
- retrieval cost
- token cost
- latency
- information density
- duplicate information
- stale context

Do not solve memory by endlessly increasing the prompt.

## 71.7 Multi-agent coordination protocols

Agent society requires explicit coordination mechanisms such as:
- delegation
- contract/task bidding where useful
- negotiation
- consensus where useful
- escalation
- shared blackboards
- typed messages
- role/capability advertisements
- conflict resolution
- cancellation propagation

The communication layer must support both hierarchical and decentralized patterns where appropriate.

## 71.8 Dynamic tool and skill creation

JARVIS must eventually be able to:
- discover a missing capability
- search existing tools
- create/adapt a tool
- test it in isolation
- register it
- version it
- reuse it

The capability system therefore needs a "capability acquisition" path, not only a static registry.

## 71.9 Self-monitoring and metacognitive control

Add explicit monitors for:
- confidence
- reasoning quality
- plan quality
- tool reliability
- memory quality
- agent health
- mission progress
- uncertainty
- goal drift
- resource consumption

When confidence is low, JARVIS should change strategy:
- seek more evidence
- create a critic
- run a simulation
- ask Creator
- choose another model
- reduce action scope

## 71.10 Reproducible agent evaluation

Agent evaluation must account for:
- non-determinism
- long-horizon effects
- retries
- context growth
- tool/environment variation
- hidden costs

Every benchmark should record:
- task definition
- environment
- model versions
- tool versions
- seed/configuration where applicable
- latency
- cost/resources
- outcome
- failures
- verification status

## 71.11 Agent/environment boundary

Every agent must declare:
- environment
- available observations
- available actions
- constraints
- resources
- permissions

An agent should not implicitly assume access to the whole world.

## 71.12 Persistent-agent continuity

Persistent agents should retain identity and long-term state across restarts when intentionally configured as persistent.

Required:
- stable agent IDs
- checkpointing
- durable memory references
- state migration
- restart recovery
- lineage

Temporary workers remain disposable.

## 71.13 Organizational topology should be adaptive

Do not permanently hard-code one hierarchy.

JARVIS should be able to select among:
- centralized
- hierarchical
- peer-to-peer
- hybrid

based on:
- task size
- risk
- latency
- communication cost
- agent count
- required expertise.

## 71.14 Generalization is an explicit objective

Test whether JARVIS can:
- transfer skills
- compose existing capabilities
- handle unseen task combinations
- adapt to new environments
- operate with unfamiliar tools
- request missing capabilities

A large number of predefined workflows is not equivalent to generality.

---

# 72. ADDITIONAL RESEARCH GAPS WE MUST TRACK

The literature audit shows several areas that remain difficult and should therefore be explicit research tracks rather than hidden assumptions:

- continual memory consolidation
- learned forgetting
- causally grounded retrieval
- multimodal embodied memory
- long-horizon planning
- reliable self-reflection
- scalable multi-agent coordination
- verifiable tool use
- interpretable/auditable decisions
- reproducible agent evaluation
- adaptation under changing environments
- goal persistence without goal drift
- robust agent communication
- safe autonomy in open-ended environments

Create a research backlog for these areas rather than pretending they are solved.

---

# 73. ACADEMIC RESEARCH INPUTS TO THE ARCHITECTURE

The system design has been cross-checked against recent research on agent architectures, memory,
hierarchical multi-agent coordination, and persistent cognitive agents.

Important conclusions incorporated:

1. Modern agent architectures converge on combinations of reasoning, planning, memory,
   world models, tool routers, critics, and environment interaction rather than a single model [R1].

2. Memory is a first-class control system with write/manage/read policies, not merely storage;
   contradiction handling, latency, privacy, consolidation, and multimodal memory are explicit
   engineering concerns [R2].

3. Hierarchical multi-agent organization with explicit sub-goals, communication, adaptive
   role allocation, and dynamic tool creation is a useful architecture for general-purpose
   task solving [R3].

4. Persistent agents require identity continuity, durable state, introspection, and mechanisms
   for long-running autonomous operation; this is a distinct systems problem from single-turn
   prompting [R4].

The builder must keep a bibliography/research-log file as implementation evolves.

[R1] [AI Agent Systems: Architectures, Applications, and Evaluation](https://consensus.app/papers/ai-agent-systems-architectures-applications-and-xu/cef04a99f48359c1860ff4d9b4be9f76/?utm_source=chatgpt) — Bin Xu, 2026, ArXiv, 16 citations.

[R2] [Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers](https://consensus.app/papers/memory-for-autonomous-llm-agentsmechanisms-evaluation-du/c39606478b3c5d80b1d7ed3513145b45/?utm_source=chatgpt) — Pengfei Du, 2026, ArXiv, 58 citations.

[R3] [AgentOrchestra: A Hierarchical Multi-Agent Framework for General-Purpose Task Solving](https://consensus.app/papers/agentorchestra-a-hierarchical-multiagent-framework-for-zhang-cui/2cfd372fee26548a8d72cf0aa55c42c8/?utm_source=chatgpt) — Wentao Zhang, Ce Cui, Yilei Zhao, Rui Hu, Yang Liu, Yahui Zhou, Bo An, 2025, ArXiv, 75 citations.

[R4] [Perpetual Self-Aware Cognitive Agents](https://www.aaai.org/ojs/index.php/aimag/article/view/2027/0) — Michael T. Cox, 2007, AI Magazine, 91 citations.

---

# 74. RESEARCH BACKLOG / OPEN QUESTIONS

OpenCode/Big Pickle must maintain:

docs/RESEARCH_BACKLOG.md

Each research item should record:
- question
- why it matters
- current hypothesis
- candidate approaches
- experiments needed
- evidence
- decision
- date reviewed
- impact on architecture

Do not freeze uncertain research questions into permanent architecture without recording the
uncertainty.

---

# 75. REQUIRED REPOSITORY FILE: RESEARCH LOG

Create:

docs/RESEARCH_LOG.md

For every architecture-changing research result, record:
- source
- date
- relevant finding
- impacted subsystem
- action taken
- unresolved questions

This turns JARVIS development into a traceable research-and-engineering process.


# 70. END STATE

The final JARVIS system should allow the Creator to do:

PHONE:
"JARVIS, what's happening?"

JARVIS:
Current missions, agents, alerts, health, and recommendations.

PHONE:
"Start the robotics mission."

JARVIS:
Creates a mission, allocates agents, selects models, launches tools, tracks progress.

PC:
Shows the same live mission and agent activity.

REMOTE:
The user can interact with the same JARVIS while away from the PC when an always-on JARVIS node is available.

JARVIS:
continues working within declared autonomy and resource boundaries until:
- mission complete
- blocked
- failed and recovered
- Creator pauses it
- Creator puts it to sleep
- Creator shuts it down

This persistent, multi-body, agentic runtime is the target.

---

# REFERENCES / CURRENT TOOLING NOTES

OpenCode's current documentation describes:
- CLI execution
- configurable agents
- tool permissions
- MCP integration
- backend/web access patterns
- model/provider configuration

Treat OpenCode documentation as the authority for the version actually installed on the user's machine.

The current OpenCode ecosystem also exposes Big Pickle as a model through OpenCode/Zen; availability and pricing/free access can change and must be checked at build time.

Do not encode temporary model availability as a permanent architectural assumption.

# 76. ARCHITECTURE INTEGRATION — JARVIS LIVING OS v2

## 76.1 Purpose of this section

This section connects the entire specification into one executable architecture. It is the canonical integration layer for DeepSeek or another engineering/reasoning model to analyze before implementation.

The purpose is NOT to require every future technology immediately. The purpose is to define stable contracts so that capabilities can be added without redesigning the kernel.

### Master principle

> **JARVIS is not the model. JARVIS is the persistent operating system that uses models.**

Models may fail, disappear, improve, be replaced, run locally, run remotely, or specialize. JARVIS identity, state, memory, missions, permissions, relationships, provenance, and history must survive model replacement.

---

# 77. THE COMPLETE JARVIS SYSTEM MODEL

```text
                         CREATOR
                            │
                  PHONE / PC / VOICE / WEB
                            │
                            ▼
                ┌────────────────────────┐
                │ INTERACTION GATEWAY    │
                │ authentication         │
                │ session continuity     │
                │ input normalization    │
                └────────────┬───────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         JARVIS KERNEL                                 │
│                                                                      │
│ Identity / Process Runtime / Scheduler / FSM / Intent Filter        │
│ Policy / Capability / Resource Governance / Attention / Interrupt   │
│ Recovery / Checkpoint / Health / Compliance / Event Coordination   │
└───────────────┬───────────────────────────────┬──────────────────────┘
                │                               │
                │ intent/work order             │ state/events
                ▼                               ▼
      ┌─────────────────┐             ┌────────────────────────┐
      │ MODEL FABRIC    │             │ EVENT LOG              │
      │ LLM/VLM/STT/TTS │             │ immutable/versioned    │
      │ VLA/VLN         │             │ causal/provenance      │
      │ simulation      │             │ replayable/exportable  │
      │ optional SNN    │             └───────────┬────────────┘
      └────────┬────────┘                         │
               │ proposals                        │ projections
               ▼                                   ▼
      ┌─────────────────┐             ┌────────────────────────┐
      │ VALIDATION      │             │ MEMORY OS              │
      │ schemas         │             │ working/episodic       │
      │ tool validation │             │ semantic/procedural    │
      │ injection       │             │ social/organizational  │
      └────────┬────────┘             └───────────┬────────────┘
               │                                  │
               ▼                                  ▼
      ┌────────────────────────────────────────────────────────┐
      │                 INTENT / POLICY PLANE                  │
      │ semantic intent → manifest → minimum capabilities     │
      │ trust / scope / budget / rate / approval / sandbox    │
      └─────────────────────────┬──────────────────────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ EFFECT SYSTEM          │
                    │ Prepare                │
                    │ Authorize              │
                    │ Commit                 │
                    │ Verify                 │
                    │ Reconcile              │
                    └───────────┬────────────┘
                                │
                                ▼
                         EXTERNAL WORLD
                files / shell / web / APIs / devices
                 Home Assistant / ROS2 / robots
                                │
                                ▼
                           OBSERVATION
                                │
                                ▼
                         WORLD MODEL UPDATE
                                │
                                └──────────────► next kernel cycle

Parallel control planes:
  SAFETY / COMPLIANCE / SELF-HEALING / RESOURCE GOVERNANCE
  continuously observe and may constrain or interrupt the main loop.
```

---

# 78. THE THREE MODELS OF REALITY

JARVIS must maintain three distinct but connected models.

## 78.1 World Model — "What is happening?"

Represents external reality:

- people
- devices
- files
- applications
- projects
- robots
- locations
- missions
- resources
- observations
- temporal state
- causal relationships
- uncertainty

World state is evidence-backed and versioned. A belief is not automatically a fact.

## 78.2 Self Model — "What can I do and how reliable am I?"

Tracks:

- available capabilities
- model abilities
- tool reliability
- known limitations
- confidence calibration
- failure modes
- stale beliefs
- current load
- resource state
- historical success rates
- skill maturity

Self-confidence is evidence-informed, not merely model-reported.

## 78.3 Organization Model — "Who should do what?"

Tracks:

- agents
- capabilities
- roles
- trust
- reputation
- competence
- relationships
- communication cost
- resource availability
- specialization
- topology
- historical team performance
- coordination patterns

This allows JARVIS to optimize not only individual intelligence but **organizational intelligence**.

---

# 79. KERNEL CONTRACT — THE JARVIS CONSTITUTION

The kernel shall:

1. Own canonical JARVIS state transitions.
2. Own process lifecycle.
3. Own scheduling.
4. Own intent mediation.
5. Own policy enforcement.
6. Own capability authorization.
7. Treat model output as untrusted proposals.
8. Mediate every external effect.
9. Preserve causal provenance.
10. Make recovery deterministic wherever possible.
11. Never silently rewrite history.
12. Never grant capabilities implicitly.
13. Never allow an agent to declare its own completion.
14. Never allow an agent to disable its own safety boundary.
15. Detect runaway computation and coordination.
16. Preserve continuity across process/model failure.
17. Permit model/provider replacement without identity loss.
18. Keep creator-owned authority distinct from learned preference.
19. Maintain an independent emergency stop path for physical systems.
20. Make all autonomous behavior auditable and replayable.

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

Models may not unilaterally:

- authorize themselves
- grant capabilities
- advance kernel state
- declare completion
- rewrite history
- disable safety controls
- change creator authority
- bypass the effect system

---

# 80. INTENT-ORIENTED SECURITY ARCHITECTURE

The original capability-only model is upgraded to an intent-mediated model.

## 80.1 Intent ABI

Every meaningful external action begins as a structured intent.

```python
class Intent(BaseModel):
    intent_id: ULID
    principal: Principal
    objective: str
    domain: str
    subject_refs: list[EntityRef]
    constraints: dict
    requested_outcome: dict
    risk_class: str
    provenance: Provenance
    work_order_id: ULID | None
```

The intent describes **what is being attempted**, not merely the API mechanism.

## 80.2 Manifest-only execution

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

The agent does not receive unrestricted primitive access merely because a primitive exists.

## 80.3 Capability remains the enforcement mechanism

Intent does not replace capability security. It sits above it.

```text
Intent = semantic security boundary
Manifest = declared execution contract
Capability = mechanical authorization boundary
Effect = actual external operation
```

## 80.4 Agent Capsule

Every agent/process may execute inside a scoped capsule containing:

- stable principal identity
- manifest
- capability grants
- filesystem scope
- network scope
- process scope
- secrets references
- resource budget
- time limit
- environment variables
- artifact workspace
- audit context
- isolation level

The capsule may map to an async task, subprocess, container, VM, TEE, remote worker, GPU worker, or robotics compute node.

## 80.5 Manifest synthesis

An intent does not execute. It compiles into a manifest. The manifest is the
declared execution contract: which contracts, under what constraints, with
what capability requirements, budget, and deadline.

Pipeline:

```text
INTENT
  ↓
CONTRACT PROPOSAL       ← LLM, schema-constrained (SCHEMA_CONSTRAINED role)
  ↓
STATIC VALIDATION       ← deterministic
  ↓
POLICY VIABILITY        ← deterministic
  ↓
MANIFEST                ← frozen, logged as intent.compiled
  ↓
CAPABILITY RESOLUTION   ← registry (not the model)
```

### Contract proposal

The model proposes a set of capability contracts and their arguments:

```yaml
proposal:
  contracts:
    - id: fs.read
      version: ^1.0
      args: { path: "/project/src" }
    - id: git.status
      version: ^1.0
      args: { repo: "/project" }
  constraints:
    network: denied
    write_access: denied
  required_capabilities:
    - READ_FS
  budget: { tokens: 20000, wall_seconds: 120 }
```

The model never names a provider. It never selects a version of a provider.
It never grants a capability. It declares only semantic contracts.

### Static validation (deterministic)

- Every contract id exists in the registry.
- Every contract version constraint resolves to at least one live provider.
- Argument schemas validate.
- The dependency graph between contracts is a DAG.
- No contract requires a capability not requested.

### Policy viability (deterministic)

- Requested capabilities are grantable to this principal.
- Budget is within mission and creator limits.
- Risk class is within the mission's autonomy level.
- Privacy class matches provider trust levels.

### Failure

If validation fails, the kernel emits `intent.rejected` with the failure
taxonomy classification. The model receives typed correction on the next
turn. The model may revise the proposal. It may not bypass validation.

### Invariant

The model proposes. Determinism disposes. Provider resolution never happens
inside a model call. Capability grant never happens inside a model call.

---

# 81. DETERMINISTIC ORCHESTRATION

JARVIS uses a deterministic finite-state orchestration layer.

## 81.1 Core lifecycle

```text
RECEIVED
  ↓
CLASSIFIED
  ↓
PLANNED
  ↓
VALIDATED
  ↓
AUTHORIZED
  ↓
EXECUTING
  ↓
OBSERVED
  ↓
VERIFIED
  ↓
COMPLETED
```

Failure branches are explicit:

```text
ANY STATE
 ├── RETRY
 ├── REPLAN
 ├── COMPENSATE
 ├── QUARANTINE
 ├── ESCALATE
 └── FAIL
```

## 81.2 Models operate inside states

The model may generate:

- a plan
- an artifact
- a classification
- a proposed intent
- a verification analysis
- a work order

The model cannot select arbitrary next states.

The deterministic orchestrator evaluates:

```text
current_state
+ event
+ validated artifact
+ evidence
+ policy
+ preconditions
+ resource state
```

and selects the next legal transition from a versioned transition table.

## 81.3 Done gate

> **The model builds. The deterministic gate decides done.**

Completion requires objective evidence appropriate to the task.

Examples:

```text
CODE
→ compile → unit tests → integration tests → behavior test

RESEARCH
→ evidence validation → contradiction check → source check

ROBOTICS
→ simulation/safety checks → controller acceptance → sensor verification

FILE OPERATION
→ existence/integrity verification

MISSION
→ all required subgoals + evidence + budget + policy conditions
```

An agent's statement "done" is evidence at most; it is never authoritative completion.

## 81.4 Versioned state machines

The vocabulary and transition rules are versioned.

New transitions require:

1. schema registration
2. static validation
3. invariant tests
4. adversarial tests
5. golden-task evaluation
6. policy review
7. version registration

---

# 82. COMPILED WORK ORDER PROTOCOL

Natural-language interaction and machine-to-machine coordination are separate layers.

```text
CREATOR / AGENT LANGUAGE
        ↓
INTENT COMPILER
        ↓
COMPILED WORK ORDER
        ↓
AGENT / EFFECT / PROTOCOL
```

Example:

```yaml
work_order:
  work_order_id: WO-...
  objective: inspect_repository
  subject_refs:
    - repository: project_17
  constraints:
    network: denied
    write_access: denied
  required_outputs:
    - findings
    - evidence_refs
  verification:
    required: true
  budget:
    tokens: 50000
    time_seconds: 300
```

Agents communicate using structured work orders, status events, artifacts, and speech acts rather than uncontrolled free-text prompt chains.

External A2A/MCP/etc. protocols are adapters into this canonical internal representation.

---

# 83. COMPLETE EFFECT PIPELINE

Every external effect follows:

```text
INTENT
  ↓
MANIFEST
  ↓
PREPARE
  ↓
AUTHORIZE
  ↓
COMMIT
  ↓
VERIFY
  ↓
OBSERVE
  ↓
EVENT
```

For missions spanning multiple effects:

```text
Mission Saga
  Step 1 → commit
  Step 2 → commit
  Step 3 → failure
             ↓
       compensation
             ↓
       Step 2 compensation
             ↓
       Step 1 compensation
```

Compensation creates new corrective events. It never erases history.

Outbox publication may be added where reliable external delivery is required.

---

# 84. MEMORY OS — COMPLETE DESIGN

Memory is a managed subsystem, not a vector database.

## 84.1 Logical memory classes

```text
WORKING
EPISODIC / TRACE
SEMANTIC / FACT / BELIEF
PROCEDURAL / SKILL
PREFERENCE
RELATIONSHIP / SOCIAL
ORGANIZATIONAL
```

## 84.2 Four logical data boundaries

```text
REGISTRY
  deterministic metadata

ENVIRONMENT
  scoped runtime parameters

SYSTEM LOGS
  immutable behavioral/audit history

MEMORY STORE
  unstructured searchable content, vectors, blobs, embeddings
```

These may be separate physical tables/databases/processes later. The architectural requirement is separation of ownership, privacy, retention, and query semantics.

## 84.3 Two-tier consolidation

```text
INPUT
 ↓
EPISODIC TRACE
 ↓
cheap search/index
 ↓
CONSOLIDATION
 ↓
EXTRACT
 ↓
VERIFY
 ↓
CONTRADICTION RESOLUTION
 ↓
PROMOTE
 ↓
SEMANTIC / PROCEDURAL MEMORY
```

Not every interaction becomes durable semantic memory.

## 84.4 Memory verification

Durable memory writes require verification proportional to impact.

```text
cheap deterministic checks
        ↓
semantic verifier
        ↓
independent verifier for high-impact memory
```

Memory classes include provenance, confidence, source, timestamp, validity state, retention policy, and supersession links.

A semantic memory is still an evidence-backed belief unless independently established as fact.

## 84.5 Retention

Every memory has an explicit policy:

- TTL
- decay
- persistent-until-corrected
- explicit-forget

Privacy-sensitive information receives stricter policy.

---

# 85. EVENT LOG AND PERSISTENCE

The event log is canonical for JARVIS state transitions.

It is:

- append-only
- immutable
- versioned
- causally linked
- provenance tracked
- replayable
- exportable
- auditable

Raw high-volume sensor data, audio, video, credentials, and large artifacts do not need to be embedded in events. Events reference content-addressed artifacts safely.

## 85.1 Event ordering

Events contain:

- global event id
- stream id
- stream sequence
- timestamp from injected Clock
- actor/principal
- event type
- schema version
- cause
- correlation id
- mission/task references
- payload
- provenance

ULID ordering is never treated as a substitute for explicit stream sequence.

## 85.2 Replay

```text
EVENT LOG
   ↓
UPCAST OLD EVENTS
   ↓
PROJECTION REBUILD
   ↓
WORLD / MEMORY / MISSION / AGENT STATE
```

Replay must produce deterministic projections.

---

# 86. CHECKPOINTING AND RECOVERY

Checkpointing is recovery-oriented, not turn-count-oriented.

## 86.1 Semantic checkpoint triggers

Mandatory or high-priority checkpoints occur:

- before irreversible effects
- after verification
- before model/provider handoff when state is material
- after important external state changes
- before risky mission transitions
- before long-running operations
- when semantic state changed materially

A semantic checkpoint decision engine may classify whether a turn changed recovery-relevant state.

OS-level inspectors such as eBPF are implementation options, not architectural requirements.

## 86.2 Snapshot metadata

Snapshots contain:

- snapshot_id
- created_at
- schema_version
- code_version
- projection_versions
- covers_up_to
- event_count
- content_hash
- previous_snapshot_hash
- projection state
- audit manifest

Canonical event history is never deleted merely because a snapshot exists.

---

# 87. SELF-HEALING IMMUNE SYSTEM

The self-healing daemon is a first-class subsystem.

```text
DETECT
  ↓
DIAGNOSE
  ↓
CLASSIFY
  ↓
SELECT RECOVERY
  ↓
RECOVER
  ↓
VERIFY HEAL
  ↓
RECORD HEAL EVENT
  ↓
PREVENT / UPDATE TESTS
```

## 87.1 Detection signals

Examples:

- SQLite integrity
- WAL stalls
- projection lag
- event-count anomalies
- memory/vector-count drift
- cross-collection sanity
- store bloat
- exportability canary
- backup freshness
- missing artifacts
- checkpoint inconsistency
- process heartbeat failures
- model-provider health

Detection produces evidence; it does not itself page the creator.

## 87.2 Recovery classes

```text
REBUILD_INDEX
REPLAY_PROJECTION
RE-EMBED_MISSING
BACKUP_MERGE_DELTA
QUARANTINE_FROM_SERVING
RESTART_WORKER
RESTORE_SNAPSHOT
FULL_REBUILD
```

Recovery is selected from corruption mode × severity × policy.

High-impact destructive repair remains policy-controlled.

## 87.3 Heal proof

A heal is not complete until a post-heal integrity check passes.

The system records:

- detected condition
- diagnosis
- selected recovery
- changes made
- verification evidence
- remaining uncertainty
- prevention action

---

# 88. AGENT RUNTIME AS A PROCESS MODEL

Agents are first-class logical processes.

Lifecycle:

```text
BORN
 ↓
INITIALIZING
 ↓
READY
 ↓
RUNNING
 ↓
SUSPENDED ↔ RESUMED
 ↓
COMPLETING
 ↓
VERIFIED
 ↓
PERSIST / TERMINATE / FAIL / EVOLVE
```

Each agent has:

- stable identity
- principal
- lineage
- parent/creator reference
- mission references
- capabilities
- manifest
- resource budget
- workspace
- memory namespace
- checkpoint state
- health heartbeat
- reputation
- version
- model assignments

An agent may survive model replacement and process restart because its identity and state live outside the model invocation.

---

# 89. AGENT CREATION AND SELF-EXTENSION

Dynamic capability acquisition follows:

```text
DETECT GAP
 ↓
SEARCH EXISTING SKILL
 ↓
COMPOSE
 ↓
AUTHOR
 ↓
STATIC ANALYSIS
 ↓
PERMISSION ANALYSIS
 ↓
SANDBOX
 ↓
ADVERSARIAL TEST
 ↓
GOLDEN TASK TEST
 ↓
VERIFICATION
 ↓
REGISTER
 ↓
MONITOR
```

No capability is acquired implicitly.

Registration requires policy approval appropriate to risk.

Every skill is versioned and rollbackable.

---

# 90. MODEL FABRIC

Models are capabilities behind adapters.

```text
ModelGateway
 ├── local LLM
 ├── cloud LLM
 ├── vision model
 ├── speech/STT
 ├── TTS
 ├── VLA/VLN
 ├── simulation/world model
 ├── specialist models
 ├── NPU/SNN backend
 └── remote compute
```

Routing considers:

- capability
- quality
- latency
- cost
- privacy
- hardware
- energy
- thermal state
- availability
- context length
- historical reliability
- circuit breaker state

Routing adapts independently from safety policy.

Model lifecycle:

```text
REGISTERED → CANARY → PROMOTED → DEPRECATED → RETIRED
```

Exact model/version is recorded in provenance.

---

# 91. COMPUTE AND ENERGY FABRIC

```python
class ComputeBackend:
    CPU
    GPU
    NPU
    SNN
    REMOTE
```

An always-on JARVIS installation must support low-power operation.

Preferred architecture:

```text
LOW-POWER PERCEPTION
  wake word / VAD / presence / anomaly
          ↓ event
JARVIS KERNEL
          ↓
EXPENSIVE COGNITION ONLY WHEN NEEDED
```

SNN/neuromorphic hardware is optional. The requirement is energy-aware routing, not dependence on a specific chip.

---

# 92. MULTIMODAL PERCEPTION

```text
RAW SENSOR / FILE / AUDIO / VIDEO
          ↓
PERCEIVER
          ↓
TYPED OBSERVATION
          ↓
PROVENANCE + UNTRUSTED FLAG
          ↓
EVENT
          ↓
WORLD MODEL
          ↓
CONTEXT ENGINE
```

Every perception source has explicit trust and provenance.

Untrusted observations can inform reasoning but cannot directly create authority.

---

# 93. COMMUNITY AND ORGANIZATION LAYER

Community is a projection of the shared event world.

Transport is infrastructure; chat is not the source of truth.

## 93.1 Structured messages

Messages contain:

- sender
- recipient/channel
- thread
- reply
- speech act
- subject/task/mission references
- artifact refs
- content
- provenance

## 93.2 Speech acts

```text
ASSERTIVE: INFORM REPORT WARN CLAIM
DIRECTIVE: REQUEST COMMAND PROPOSE SUGGEST
COMMISSIVE: PROMISE OFFER ACCEPT DECLINE
EXPRESSIVE: ACKNOWLEDGE THANK APOLOGIZE
DECLARATION: DECLARE REVOKE ESCALATE
```

Speech acts determine downstream protocol handling.

## 93.3 Coordination protocols

Versioned state machines:

- delegation
- bidding
- negotiation
- consensus
- escalation
- cancellation
- handoff
- verification

## 93.4 Organization topology

Potential organizational graph:

```text
all eligible agents
        ↓
Topology Selector
        ↓
Sparse Active Coordination Graph
        ↓
Execution
```

Supported strategy classes:

```text
heuristic
learned
search_based
```

Topologies may include:

```text
SOLO
HIERARCHICAL
MARKET
PEER
HYBRID
SPARSE-HYBRID
```

The organization itself is evaluated as a performance variable.

---

# 94. TRUST, REPUTATION, AND VERIFICATION

Separate these concepts:

```text
competence ≠ trust ≠ reputation ≠ authority ≠ permission
```

Reputation may affect routing and delegation.

Trust may affect context and verification frequency.

**Trust never removes mandatory verification for irreversible effects.**

Reputation updates from:

- verification outcomes
- promise keeping
- successful task completion
- failures
- recency
- domain competence

Repeated failures may trigger quarantine.

---

# 95. ATTENTION AND CREATOR COORDINATION

Creator interaction is a coordination surface, not merely chat.

JARVIS models:

```text
SALIENCE
INVOLVEMENT
ACTIVITY
```

## 95.1 Coordination states

```text
DONE-WITH-ME
ASSISTED
DONE-FOR-ME
AUTONOMOUS
```

Transitions depend on demonstrated reliability, task risk, creator preference, and policy.

## 95.2 Workplan gates

A mission may define:

- approval points
- notification points
- review checkpoints
- escalation conditions
- silence periods
- required evidence

## 95.3 Responsive salience

High-risk or low-trust situations increase visibility and explanation. Routine trusted work becomes quieter.

The creator is not asked to approve every low-risk action simply because the system is autonomous.

---

# 96. LOOP, TOKEN, AND RESOURCE GOVERNANCE

JARVIS must detect:

- repeated intent signatures
- oscillating plans
- no-progress loops
- recursive delegation
- runaway spawning
- repeated failed effects
- token avalanche
- budget exhaustion
- resource starvation

```text
LOOP DETECTED
 ↓
PAUSE / CIRCUIT BREAK
 ↓
DIAGNOSE
 ↓
REPLAN
 ↓
ESCALATE if unresolved
```

Budgets apply to:

- tokens
- time
- CPU
- GPU
- memory
- network
- external API cost
- agent count
- effect count
- energy

---

# 97. CONTINUOUS SAFETY AND COMPLIANCE

Safety is a running process.

```text
BASELINE MONITORING
        ↓
RISK-TRIGGERED PROBING
        ↓
DEEP RED TEAM
        ↓
QUARANTINE / STOP / REMEDIATE
```

Safety boundary is multidimensional:

```text
agent × capability × domain × model_version × environment
```

Examples:

- safe for code review but unsafe for robotics
- safe locally but unsafe with external network
- safe for read-only work but unsafe with write access
- safe model version but unsafe modified model

Every model modification must pass post-modification safety and alignment evaluation before deployment. Specific methods such as PING are optional implementations, not invariants.

---

# 98. TERMINAL VERIFICATION / CORRECTION GATE

Every important linear agent pipeline ends in a terminal verification/correction stage.

```text
WORKER
 ↓
ARTIFACT
 ↓
VERIFY
 ├── PASS → commit gate
 └── FAIL → CORRECT → VERIFY AGAIN
```

This stage may be a lightweight deterministic checker, specialist verifier, model verifier, simulator, test suite, or combination.

The architecture does not depend on a particular named "Fixer" model.

---

# 99. EXTERNAL PROTOCOLS

JARVIS uses adapters rather than protocol lock-in.

```text
A2A ─────┐
MCP ─────┤
HTTP ────┤
ROS2 ────┤
WebSocket┤
custom ───┘
     ↓
Protocol Adapter
     ↓
Canonical JARVIS Work Order / Event
```

A2A may be the preferred external agent-to-agent federation protocol where appropriate. It must not become the canonical internal state representation.

---

# 100. ROBOTICS AND PHYSICAL EMBODIMENT

Robotics is a layered body, not a special exception.

```text
JARVIS EXECUTIVE
       ↓
ROBOT MISSION EXECUTIVE
       ↓
EMBODIED PLANNER
       ↓
WORLD MODEL / DIGITAL TWIN
       ↓
VLA / VLN / ACTION MODEL
       ↓
ROS2
       ↓
REAL-TIME CONTROLLER
       ↓
ACTUATOR
       ↓
SENSOR
       ↓
OBSERVATION
       └──────────────→ WORLD MODEL
```

Learned models do not replace deterministic real-time safety controllers.

Physical emergency stop is independent of JARVIS software.

---

# 101. DIGITAL TWIN AND COUNTERFACTUAL REASONING

For expensive, risky, or irreversible actions:

```text
candidate action
 ↓
world model
 ↓
simulation / counterfactual
 ↓
expected outcomes
 ↓
risk analysis
 ↓
verification
 ↓
commit / reject / escalate
```

Gazebo, Isaac, simulators, CAD, MATLAB/Simulink, and future world models are capability adapters rather than kernel dependencies.

---

# 102. HOME / IOT BODY

Home Assistant or equivalent acts as a device integration layer.

```text
DEVICE STATE CHANGE
 ↓
PERCEPTION EVENT
 ↓
WORLD MODEL
 ↓
MISSION / POLICY
 ↓
INTENT
 ↓
EFFECT
 ↓
PHYSICAL CHANGE
 ↓
OBSERVATION
```

This creates a closed-loop physical world model.

---

# 103. PHONE AS JARVIS BODY

The phone is a body/interface of the same JARVIS identity, not a second assistant.

It provides:

- voice
- microphone
- camera
- display
- notifications
- location when explicitly enabled
- remote control
- emergency stop
- offline command queue

The phone may cache state but canonical identity/state remain with the JARVIS persistence layer.

Camera/microphone/location capabilities are explicit, scoped, revocable, and audited.

---

# 104. ALWAYS-ON DEPLOYMENT

## Stage A — Development

Laptop:

```text
systemd user service
SQLite WAL
local models
local tools
```

## Stage B — Real always-on node

Preferred planning target:

```text
used mini-PC / N100-class or similar
16 GB+ RAM
Debian/Linux
Docker or systemd
```

Laptop becomes a high-compute/development/robotics client.

## Stage C — Optional GPU node

GPU worker joins the compute fabric.

## Stage D — Optional cloud failover

VPS/cloud node can assume selected workloads when configured.

## Continuity

```text
PHONE
  ↕ secure mesh
ALWAYS-ON JARVIS NODE
  ↕
GPU / LAPTOP / ROBOT / CLOUD
```

Tailscale/WireGuard or equivalent secure networking may be used.

The system remains logically alive even if one execution node fails because state is persistent and recoverable.

---

# 105. IDENTITY AND BOOTSTRAP

First-run sequence:

```text
jarvis init
 ↓
creator keypair
 ↓
secure key storage
 ↓
creator.initialized event
 ↓
local kernel
 ↓
projection initialization
 ↓
localhost API
 ↓
one-time pairing code
 ↓
phone/device pairing
```

Creator identity is a cryptographic principal.

Device compromise response:

```text
principal revoke
secret rotate
incident open
capabilities invalidate
```

### 105.1 Registry bootstrap

`jarvis init` seeds the registry with a curated set of first providers
(filesystem, terminal, one local model adapter, HTTP client). Each seeded
provider carries full supply-chain metadata.

Authority:

- The creator principal is the sole initial holder of:
  - `REGISTER_PROVIDER`
  - `PROMOTE_PROVIDER`
  - `REVOKE_PROVIDER`
  - `GRANT_CAPABILITY`
- Agent principals may emit `capability.provider_proposed`.
- Only the creator principal may emit `capability.provider_added`.
- No principal may self-grant. No principal may register a provider that
  expands its own capabilities.

### 105.2 Provider registration ceremony

Registration is a two-step event pair:

1. `capability.provider_proposed` — by any principal, with metadata
2. `capability.provider_added` — by creator only, with signed approval

The registry is unusable for a proposed provider until step 2.

---

# 106. SECRETS ARCHITECTURE

Secrets are capability-scoped resources.

They must not be treated as ordinary environment variables or placed in the event log.

```text
SECRET STORE
 ↓ reference
CAPABILITY GRANT
 ↓
EFFECT / GATEWAY
```

The model receives neither raw credentials nor arbitrary secret-store access.

Supported implementation tiers may include OS keyring, encrypted age-backed storage, hardware-backed secrets, or remote secret managers.

---

# 107. FAILURE TAXONOMY

Every failure is classified where possible:

```text
TRANSIENT
RATE_LIMITED
AUTH
BUDGET
INVALID_INPUT
DEPENDENCY_DOWN
TIMEOUT
CONFLICT
POLICY
BUG
UNKNOWN
```

Recovery is a deterministic policy mapping:

```text
FailureKind × EffectKind → RecoveryAction
```

Every production incident produces:

- incident event
- cause/timeline
- recovery result
- counterfactual analysis where useful
- golden test candidate
- threat-model update when appropriate

---

# 108. SLEEP / WAKE / CONTINUITY

JARVIS lifecycle states:

```text
RUNNING
IDLE
SLEEPING
DEGRADED
EMERGENCY
SHUTDOWN
```

SLEEPING means background autonomy under a maintenance policy, not absence of execution.

Sleep tasks may include:

- checkpointing
- memory consolidation
- backup
- regression evaluation
- reputation update
- maintenance
- expired-data pruning
- credential rotation
- health checks

A wake event returns the system to an appropriate active state.

---

# 109. TIME AND SCHEDULING

All internal timestamps are UTC.

Schedules are represented as:

```text
local_time
+ timezone_name
+ recurrence_rule
```

Scheduler computes local occurrence then converts to UTC.

DST adjustments are explicit events.

All time access goes through an injected Clock:

```text
SystemClock
FrozenClock
ScaledClock
```

No business logic may directly call system time when deterministic replay matters.

---

# 110. OBSERVABILITY AND EXPLAINABILITY

Every mission should be traceable across:

```text
trace_id
span_id
parent_span_id
```

`jarvis explain <event_id>` should eventually provide:

- cause chain
- state transitions
- prompt versions
- model/version
- outputs
- retrieved memory references and scores
- world-state slice
- intent
- capability checks
- policy decisions
- budget
- verification
- alternative proposals
- confidence/uncertainty
- artifacts

The explanation is generated from recorded evidence, not reconstructed from memory after the fact.

### 110.1 Required span names and attributes

Every event is a span. Every model call, effect, and verification is a child.

| Span name | Emitted for |
|---|---|
| `jarvis.event` | every event appended to the log |
| `jarvis.model.call` | every model gateway invocation |
| `jarvis.effect.{name}` | every effect commit |
| `jarvis.verify.{name}` | every verification |
| `jarvis.policy.check` | every authorization decision |
| `jarvis.registry.resolve` | every contract → provider resolution |

Required attributes on every span:

- `event.id`
- `principal.id`
- `mission.id` (when applicable)
- `task.id` (when applicable)

Additional attributes by span type:

- model.call: `model.name`, `model.version`, `prompt.version`, `contract.id`
- effect.*: `contract.id`, `contract.version`, `provider.id`, `provider.version`
- policy.check: `capability.requested`, `policy.result`
- registry.resolve: `contract.id`, `contract.version`, `provider.id`

Conventions live in `docs/OBSERVABILITY.md`. New spans require a schema.

---

# 111. REPRODUCIBILITY AND EVALUATION

Prompt construction must be deterministic for identical inputs/configuration.

No hidden `now()`, unstable set ordering, random dictionary ordering, unstable repr, or uncontrolled environment reads in deterministic prompt paths.

Record/replay:

```text
prompt_hash
→ recorded model response
→ deterministic reproduction
```

Evaluation classes:

1. unit tests
2. property-based tests
3. integration tests
4. golden tasks
5. long-horizon tasks
6. multi-session tasks
7. adversarial safety tests
8. organizational topology comparisons
9. recovery/failure drills
10. end-to-end application behavior tests

Every significant production failure becomes a regression case where practical.

---

# 112. PROPERTY INVARIANTS

The following are non-negotiable test targets:

```text
rebuilding projections twice gives identical state
causal links point backward or null
correlation graph contains no cycles
committed effect has authorized intent
idempotent effect does not duplicate external outcome
budget spent does not exceed allocation without override
replay reproduces final projection
hard deny cannot be bypassed by model output
agent cannot self-grant capabilities
agent cannot self-declare completion
irreversible effect has required verification
canonical history is never rewritten
secret material never enters durable event payloads
quarantine revokes active grants according to policy
cancellation propagates through causal task graph
loop circuit breakers stop no-progress recursion
memory promotion requires required verification
```

---

# 113. EMERGENCY SAFETY ARCHITECTURE

Two safety planes exist.

## Software plane

```text
STOP_AGENT
STOP_MISSION
STOP_ALL_SOFT
STOP_ALL_HARD
```

## Independent physical plane

```text
hardware watchdog
motor controller safety
relay / power cutoff
physical emergency stop
```

The physical safety plane must not depend on JARVIS continuing to execute.

Phone emergency stop should use the shortest trusted route to the physical safety controller where possible.

---

# 114. BACKUP AND DISASTER RECOVERY

Target:

```text
nightly encrypted backups
2 independent locations
WAL shipping where appropriate
RPO ≤ 1 hour target
RTO ≤ 4 hours target
quarterly fresh-machine restore drill
```

A backup is not considered valid merely because it exists. Restore must be periodically demonstrated.

---

# 115. RESEARCH EVIDENCE REGISTRY

Research informs architecture but does not automatically become architecture.

```python
class ResearchClaim(BaseModel):
    claim_id: ULID
    source: ArtifactRef
    publication_date: datetime | None
    claim: str
    evidence_level: Literal[
        "hypothesis",
        "preliminary",
        "replicated",
        "production_validated"
    ]
    applicable_domain: list[str]
    architectural_implication: str
    confidence: float
    status: Literal[
        "observed",
        "experimental",
        "accepted",
        "rejected",
        "superseded"
    ]
```

Lifecycle:

```text
RESEARCH
 ↓
CLAIM
 ↓
EVIDENCE ASSESSMENT
 ↓
EXPERIMENT
 ↓
JARVIS EVALUATION
 ↓
ARCHITECTURAL DECISION
 ↓
PRODUCTION EVIDENCE
```

Specific papers, models, algorithms, hardware, and benchmarks are never architectural invariants when an abstraction can preserve the capability.

---

# 116. TECHNOLOGY ABSTRACTIONS

The architecture intentionally avoids hard dependencies on:

- a single LLM
- a single agent framework
- a single vector database
- a single message bus
- a single robotics model
- a single simulator
- a single protocol
- a single neuromorphic chip
- a single cloud provider

Current practical implementation target remains deliberately small:

```text
Python 3.12 (pinned: requires-python = ">=3.12,<3.14" per ADR-008; uv's default 3.14 interpreter is outside the contract window)
FastAPI
Pydantic v2
SQLite WAL
asyncio
Ollama / OpenAI-compatible model adapters
pytest / pytest-asyncio
uv
systemd / Docker later
```

Scale-out replacements remain adapters:

```text
SQLite → PostgreSQL
asyncio → NATS/other durable transport
local model → provider fabric
single node → multi-node
local robot → distributed robotics
```

Do not introduce Kafka, Kubernetes, Redis, graph databases, vector databases, or giant agent frameworks merely because they exist. Introduce them only when a measured requirement justifies them.

---

# 117. FULL EXECUTION PIPELINE — ONE REQUEST

This is the canonical end-to-end execution proof path.

```text
1. CREATOR INPUT
      ↓
2. AUTHENTICATE PRINCIPAL
      ↓
3. CREATE message.received EVENT
      ↓
4. UPDATE PROJECTIONS
      ↓
5. ATTENTION / PRIORITY CLASSIFICATION
      ↓
6. DETERMINE EXISTING MISSION OR CREATE MISSION
      ↓
7. DETERMINISTIC FSM ENTERS CLASSIFY/PLAN
      ↓
8. CONTEXT ENGINE BUILDS BOUNDED CONTEXT
      ↓
9. MODEL GENERATES STRUCTURED PLAN
      ↓
10. SCHEMA VALIDATION
      ↓
11. PLAN STATIC VALIDATION
      ↓
12. CREATE INTENT / WORK ORDERS
      ↓
13. INTENT POLICY CHECK
      ↓
14. MANIFEST SYNTHESIS
      ↓
15. MINIMUM CAPABILITIES GRANTED
      ↓
16. AGENT CAPSULE CREATED/REUSED
      ↓
17. RESOURCE BUDGET CHECK
      ↓
18. RATE LIMIT / BACKPRESSURE CHECK
      ↓
19. PREPARE EFFECT
      ↓
20. AUTHORIZE EFFECT
      ↓
21. COMMIT EFFECT
      ↓
22. OBSERVE RESULT
      ↓
23. VERIFY RESULT
      ↓
24. TERMINAL CORRECTION GATE IF NEEDED
      ↓
25. RECORD EFFECT + RESULT + EVIDENCE
      ↓
26. UPDATE WORLD MODEL
      ↓
27. UPDATE EPISODIC TRACE
      ↓
28. MEMORY PROMOTION CANDIDATE
      ↓
29. MEMORY VERIFICATION
      ↓
30. PROMOTE DURABLE MEMORY IF APPROVED
      ↓
31. SELF-MODEL UPDATE
      ↓
32. ORGANIZATION / REPUTATION UPDATE
      ↓
33. DETERMINISTIC DONE GATE
      ↓
34. MISSION COMPLETED OR REPLAN
      ↓
35. CREATOR-FACING RESULT
      ↓
36. TRACEABLE AUDIT RECORD
```

At every stage, parallel safety/resource/health monitors may interrupt execution.

---

# 118. FULL EXECUTION PIPELINE — MULTI-AGENT MISSION

```text
CREATOR GOAL
 ↓
MISSION
 ↓
PLANNER
 ↓
TASK GRAPH
 ↓
ORGANIZATION MODEL
 ↓
TOPOLOGY SELECTOR
 ↓
SPARSE ACTIVE AGENT GRAPH
 ↓
WORK ORDERS
 ↓
AGENTS EXECUTE
 ↓
BLACKBOARD / ARTIFACTS / EVENTS
 ↓
VERIFIERS
 ↓
CONFLICT RESOLUTION
 ↓
SYNTHESIS
 ↓
TERMINAL GATE
 ↓
MISSION COMPLETE
```

The system may select:

```text
SOLO
HIERARCHICAL
PEER
MARKET
CONSENSUS
HYBRID
SPARSE-HYBRID
```

based on measured mission properties.

Experimental mechanisms such as game-theoretic allocation, market pricing, imitation learning, MCTS/DPP topology selection, or learned organization are plugins rather than kernel requirements.

---

# 119. FULL FAILURE EXECUTION PROOF

A mission is considered architecturally robust only when failures follow controlled paths.

### Model unavailable

```text
MODEL CALL
 ↓
CIRCUIT BREAKER
 ↓
FALLBACK MODEL / DEFER
 ↓
DEGRADED MODE
 ↓
EVENT
```

### Malformed model output

```text
MODEL
 ↓
SCHEMA VALIDATION FAIL
 ↓
RETRY / CORRECTION
 ↓
ESCALATE OR FAIL
```

### Duplicate effect request

```text
INTENT
 ↓
IDEMPOTENCY KEY
 ↓
EXISTING RESULT
 ↓
RETURN EXISTING RESULT
```

### Crash during commit

```text
PREPARE
 ↓
AUTHORIZE
 ↓
COMMIT
 ↓ CRASH
RECOVERY
 ↓
RECONCILE EXTERNAL WORLD
 ↓
VERIFY
 ↓
CONTINUE / COMPENSATE
```

### Corrupted projection

```text
INTEGRITY CHECK
 ↓
DIAGNOSE
 ↓
QUARANTINE BAD PROJECTION
 ↓
REPLAY / SNAPSHOT RESTORE
 ↓
VERIFY
 ↓
SERVE
```

### Prompt injection

```text
UNTRUSTED INPUT
 ↓
OBSERVATION / DATA
 ↓
MODEL CONTEXT
 ↓
MODEL PROPOSAL
 ↓
INTENT BOUNDARY
 ↓
POLICY / CAPABILITY DENIAL
 ↓
AUDIT
```

The injected text never becomes authority merely because the model read it.

### Agent runaway

```text
LOOP / RESOURCE MONITOR
 ↓
CIRCUIT BREAKER
 ↓
PAUSE
 ↓
QUARANTINE IF REQUIRED
 ↓
KILL / RESTART / REPLAN
 ↓
AUDIT
```

### Agent compromise

```text
ANOMALY
 ↓
SAFETY BOUNDARY
 ↓
QUARANTINE
 ↓
REVOKE GRANTS
 ↓
TERMINATE PROCESS TREE
 ↓
PRESERVE EVIDENCE
 ↓
CREATE SUCCESSOR ONLY IF POLICY ALLOWS
```

---

# 120. FULL PROOF OF CONTINUITY

The minimum proof that JARVIS is a persistent system rather than a chatbot is:

```text
RUN 1
creator says: remember X
 ↓
X becomes verified memory
 ↓
shutdown process

RUN 2
kernel restarts
 ↓
replay event log
 ↓
rebuild projections
 ↓
recover identity
 ↓
retrieve X
 ↓
continue mission
```

Additional continuity proof:

```text
MODEL A unavailable
 ↓
MODEL B selected
 ↓
same JARVIS identity
 ↓
same mission
 ↓
same memory
 ↓
same permissions
 ↓
new provenance
```

Therefore identity belongs to the operating system, not the model.

---

# 121. FULL PROOF OF SAFETY

A system is not considered autonomous-safe because a model is aligned.

Safety must hold even when:

- model is wrong
- model hallucinates
- prompt is malicious
- tool output is poisoned
- agent is compromised
- agent loops
- provider fails
- memory is corrupted
- network is hostile
- creator is offline
- hardware partially fails

The safety proof is architectural:

```text
untrusted proposal
 ↓
structured validation
 ↓
intent mediation
 ↓
manifest restriction
 ↓
capability authorization
 ↓
policy enforcement
 ↓
effect protocol
 ↓
verification
 ↓
audit
```

No single model behavior is the safety boundary.

---

# 122. FULL PROOF OF "LIVING" BEHAVIOR

JARVIS qualifies as a living computational system when it demonstrates all of the following simultaneously:

```text
IDENTITY
  persistent principal

CONTINUITY
  state survives process/model restart

PERCEPTION
  receives observations from world/body

MEMORY
  managed long-term state

INITIATIVE
  scheduler and event triggers can create work

GOALS
  persistent missions and obligations

ACTION
  effects mediated into external world

OBSERVATION
  verifies consequences

LEARNING
  improves memory, skills, routing, organization

SELF-MODEL
  tracks abilities and limitations

ORGANIZATION
  manages other agents and teams

GOVERNANCE
  policy, authority, capabilities, reputation

SELF-HEALING
  detects and repairs bounded failures

PRESENCE
  remains available while creator is absent
```

No individual feature proves life. The integrated closed loop does.

---

# 123. BUILD PHASES — FINAL CONNECTED ROADMAP

## M0 — Machine and Environment Audit

Before modifying the system:

1. inspect machine
2. inspect CPU/RAM/GPU/storage
3. inspect OS
4. inspect Python/runtimes
5. inspect installed AI tools
6. inspect Ollama/providers
7. inspect OpenCode configuration
8. inspect MCP/tools
9. inspect network
10. inspect repositories
11. inspect available engineering software
12. identify constraints
13. produce plan
14. wait for approval before destructive changes

## M1 — Kernel Substrate

Build:

- event log
- event schemas/versioning
- Clock
- principals
- deterministic FSM
- intent schema
- manifest schema
- capability kernel
- effect envelope
- structured output validation
- basic context engine
- SQLite WAL
- CLI
- tests

Proof:

```text
hello
→ event
→ model
→ response
→ restart
→ replay
→ remembered state
```

## M2 — Memory + First Tool Body

Build:

- episodic traces
- memory API
- consolidation pipeline
- memory verification
- filesystem effect
- sandbox
- intent-to-manifest compilation
- compiled work orders
- loop breaker
- budgets/rate limits

Proof:

```text
read file
→ evidence
→ memory trace
→ restart
→ recover
```

## M3 — Missions + Persistent Processes

Build:

- mission graph
- scheduler
- persistent agents
- checkpoints
- semantic recovery
- Saga/compensation
- verifier
- terminal done gate
- health daemon
- self-healing foundations

Proof:

```text
mission running
→ crash
→ recover
→ resume
→ verify
→ complete
```

## M4 — Agent Society + Coordination

Build:

- agent factory
- lifecycle
- lineage
- communication projection
- speech acts
- work orders
- blackboard
- artifact registry
- delegation
- presence
- reputation
- topology selection
- organization model
- coordination surface

Proof:

```text
mission
→ team formation
→ delegation
→ execution
→ verification
→ synthesis
→ completion
```

## M4.5 — Reliability Gate

Before major autonomy expansion, require:

- replay tests
- property tests
- semantic checkpoint tests
- failure drills
- self-healing drills
- prompt injection tests
- memory corruption tests
- loop tests
- model outage tests
- Saga recovery tests
- golden tasks
- deterministic FSM validation

No M5 autonomy expansion until this gate passes.

## M5 — Cognitive Expansion

Build:

- advanced planner
- HTN methods
- attention
- metacognition
- self-model
- adaptive routing
- skill acquisition
- creator preference learning
- continuous compliance
- model lifecycle
- multimodal perception
- advanced organization optimization

## M6 — Living Deployment

Build:

- always-on node
- phone body
- voice
- low-power perception
- secure remote access
- background missions
- backup/DR
- self-healing operations
- cross-device continuity

## M7 — Embodiment

Build:

- ROS2
- robot body
- VLA/VLN adapters
- digital twin
- Gazebo/Isaac/simulation adapters
- real-time controller integration
- physical safety plane
- embodied mission verification

## M8+ — Evolution

Experimental capabilities may include:

- market coordination
- learned organization
- game-theoretic coordination
- multi-agent imitation
- neuromorphic hardware
- TEE-backed execution
- federation
- advanced world models
- self-development
- selective fine-tuning

Only evidence justifies promotion from experiment to core architecture.

---

# 124. DEFINITION OF DONE FOR THE WHOLE SYSTEM

JARVIS is not "done" because a chat interface works.

The architecture is considered operationally mature when all of these can be demonstrated:

### Identity

- creator identity survives restart
- device pairing works
- compromised principals can be revoked

### Persistence

- event log survives process failure
- projections rebuild
- checkpoints restore
- backups restore on fresh hardware

### Cognition

- model proposals are schema-constrained
- deterministic FSM controls transitions
- context is bounded and reproducible
- planner can replan

### Action

- intent precedes external effects
- minimum capabilities are synthesized
- effects use prepare/authorize/commit/verify
- idempotency works
- Saga compensation works

### Memory

- traces survive restart
- semantic memory requires verification
- contradictions are represented
- retention policies execute

### Agents

- agents have lifecycle and identity
- agents can be spawned/reused/terminated
- lineage is preserved
- agents cannot self-authorize

### Community

- agents communicate via structured protocols
- work orders minimize context pollution
- coordination topology is measurable
- loops are detected

### Safety

- prompt injection cannot directly create authority
- hard denies are non-bypassable
- continuous compliance operates
- physical stop is independent

### Recovery

- model failure is survivable
- DB/projection failure is survivable
- process failure is survivable
- selected corruption classes self-heal

### Living behavior

- JARVIS can continue a mission while creator is absent
- JARVIS can wake from events/timers
- JARVIS can observe consequences
- JARVIS can learn verified improvements
- JARVIS can coordinate multiple agents

---

# 125. ARCHITECTURE FREEZE RULE

The architecture is now frozen at the abstraction level.

A new core component may be added only when at least one is demonstrated:

1. a concrete unmet requirement
2. a reproducible failure case
3. measured performance evidence
4. security evidence
5. recovery evidence
6. an implementation constraint that cannot be solved through an existing abstraction

Do not add architecture because it sounds more intelligent, futuristic, fashionable, or academically interesting.

Experiments remain plugins until evidence promotes them.

### 125.1 Enforcement

After M1 lands, this document changes only when code changes force it.

Rules:

- New sections are refused by default.
- Gaps are filled in place, never by appending.
- Architectural additions require the same evidence standard as new core
  components (see §125 items 1–6).
- Every change to this file must cite the code change, failure, or measured
  result that forced it.
- Spec changes without a corresponding code change or failing test are
  labeled `SPECULATIVE` and marked for removal at the next review.

The document's purpose is to describe the system that exists and the
constraints the system must honor. Not the system that might exist.

---

# 126. DEEPSEEK ANALYSIS INSTRUCTIONS

This document is an engineering specification, not a request to blindly implement every line.

When analyzing this specification:

## First

Audit the entire architecture for:

- contradictions
- missing interfaces
- circular dependencies
- unsafe authority paths
- nondeterministic control paths
- impossible guarantees
- unnecessary infrastructure
- implementation sequencing errors
- resource bottlenecks
- security gaps
- recovery gaps
- evaluation gaps

## Second

Build an explicit dependency graph:

```text
KERNEL
 → EVENT
 → IDENTITY
 → FSM
 → INTENT
 → POLICY
 → CAPABILITY
 → EFFECT
 → PERSISTENCE
 → PROJECTION
 → MEMORY
 → PROCESS
 → MISSION
 → COMMUNITY
 → LEARNING
 → BODY
 → ROBOTICS
```

Identify which nodes are foundational and which are optional.

## Third

Produce an implementation plan that distinguishes:

```text
MUST BUILD NOW
BUILD AFTER FOUNDATION
OPTIONAL PLUGIN
RESEARCH EXPERIMENT
FUTURE HARDWARE
```

## Fourth

For every subsystem provide:

- interface
- schema
- inputs
- outputs
- state ownership
- failure modes
- security boundary
- tests
- acceptance criteria
- dependencies

## Fifth

Generate an invariant matrix showing which kernel rule protects which failure mode.

## Sixth

Generate an end-to-end execution trace for at least:

1. simple conversation
2. memory write
3. file read
4. multi-step mission
5. multi-agent mission
6. failed model call
7. prompt injection
8. duplicate effect
9. crash during commit
10. corrupted projection
11. self-healing event
12. robot mission

## Seventh

Do not begin destructive implementation until the machine audit and repository audit are complete.

## Eighth

When implementation begins, implement vertically through one proven slice rather than creating empty abstractions for every future subsystem.

---

# 127. FIRST VERTICAL SLICE — PROOF BEFORE SCALE

The first executable JARVIS slice must be:

```text
creator
 ↓
CLI
 ↓
message.received
 ↓
projection
 ↓
context engine
 ↓
model adapter
 ↓
structured response
 ↓
deterministic FSM
 ↓
event log
 ↓
restart
 ↓
replay
 ↓
state recovery
```

Then add:

```text
creator
 ↓
intent
 ↓
manifest
 ↓
READ_FS capability
 ↓
fs.read effect
 ↓
verification
 ↓
evidence
 ↓
event
```

Then:

```text
mission
 ↓
scheduler
 ↓
persistent agent
 ↓
checkpoint
 ↓
crash simulation
 ↓
recovery
 ↓
verification
 ↓
completion
```

Only after these three proofs should the agent factory and society be expanded.

### 127.1 M1 acceptance test — pass/fail

M1 is done when, on a fresh machine, this exact sequence succeeds:

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

And these must all pass:

- `pytest -q` green
- property invariants from §112 green
- `jarvis replay --verify` produces identical projection hashes
- second restart is idempotent (no duplicate events)
- the registry reflects exactly the seeded providers, no agent-registered ones

If any of the above fails, M1 is not done. Do not proceed to M2.

---

# 128. THE SINGLE UNIFYING LOOP

Everything in JARVIS ultimately reduces to this closed loop:

```text
                    ┌───────────────────────┐
                    │       IDENTITY        │
                    └───────────┬───────────┘
                                ↓
                         PERCEIVE WORLD
                                ↓
                         UPDATE WORLD MODEL
                                ↓
                         DETERMINE INTENT
                                ↓
                      BUILD / UPDATE MISSION
                                ↓
                      PLAN / CREATE WORK ORDER
                                ↓
                       DETERMINISTIC GATE
                                ↓
                        POLICY + MANIFEST
                                ↓
                         CAPABILITIES
                                ↓
                            EFFECT
                                ↓
                         REAL WORLD
                                ↓
                          OBSERVATION
                                ↓
                           VERIFY
                                ↓
                     MEMORY / SELF MODEL
                                ↓
                      ORGANIZATION MODEL
                                ↓
                         LEARN / ADAPT
                                ↓
                    SCHEDULE NEXT ACTIVITY
                                ↓
                         ─── REPEAT ───
```

The safety loop runs alongside it:

```text
MONITOR → DETECT → DIAGNOSE → CONSTRAIN / HEAL → VERIFY
```

The persistence loop runs underneath it:

```text
EVENT → LOG → PROJECT → CHECKPOINT → REPLAY
```

The organizational loop runs around agents:

```text
CAPABILITIES → TOPOLOGY → DELEGATION → PERFORMANCE → REPUTATION → REORGANIZE
```

These are not four different systems. They are four views of one operating organism.

---

# 129. FINAL ARCHITECTURAL COMMANDMENT

> **The model is replaceable. The kernel is authoritative. The event history is canonical. Intent is mediated. Capabilities are least-privilege. Effects are verified. Memory is earned. Agents are processes. Completion is proven. Failures are recoverable. Safety is continuous. The creator is the authority. The system remains alive through persistent state, scheduling, perception, action, observation, learning, and recovery.**

The long-term goal is not to build a chatbot with many tools.

The goal is to build a **persistent computational organism** that can acquire new capabilities without surrendering control of its own safety, state, or identity.

---

# 130. CURRENT ARCHITECTURE STATUS

```text
ARCHITECTURE: FROZEN AT ABSTRACTION LEVEL

FOUNDATION:
  Event-sourced deterministic kernel        ACCEPTED
  Intent-oriented security                  ACCEPTED
  Deterministic orchestration               ACCEPTED
  Capability authorization                  ACCEPTED
  Effect transaction protocol               ACCEPTED
  Persistent process model                 ACCEPTED
  Memory OS                                ACCEPTED
  Self-healing                             ACCEPTED
  Continuous safety                        ACCEPTED

SCALABLE CAPABILITIES:
  Multi-agent society                       ACCEPTED
  Adaptive organization                     ACCEPTED
  Model fabric                              ACCEPTED
  Multimodal perception                     ACCEPTED
  Voice                                     ACCEPTED
  Phone body                                ACCEPTED
  Always-on node                            ACCEPTED
  Robotics                                  ACCEPTED
  Digital twin                              ACCEPTED

OPTIONAL / EXPERIMENTAL:
  TEE                                       PLUGGABLE
  SNN / neuromorphic                        PLUGGABLE
  Market economy                            EXPERIMENTAL
  Game-theoretic coordination               EXPERIMENTAL
  Learned topology                          EXPERIMENTAL
  Multi-agent imitation                     EXPERIMENTAL
  Specific VLA/VLN models                   REPLACEABLE
  Specific A2A/MCP versions                 ADAPTERS

NEXT ACTION:
  STOP ARCHITECTURE EXPANSION
  ↓
  AUDIT REAL MACHINE
  ↓
  CREATE ARCHITECTURE CONTRACT
  ↓
  IMPLEMENT M1
  ↓
  PROVE VERTICAL SLICE
  ↓
  EXPAND ONLY FROM EVIDENCE
```


---

# 131. EXTERNAL CAPABILITY REGISTRY — THE SUBSTITUTION SEAM

## 131.1 Purpose

The External Capability Registry is the formal substitution seam between JARVIS and every external tool, service, model-serving system, library-backed capability, protocol implementation, or hardware-facing provider.

It is NOT merely a configuration file. It is a versioned, auditable runtime projection over capability registration events.

The architectural rule is:

> **JARVIS code depends on stable capability contracts. Providers are replaceable implementations behind JARVIS-owned adapters. No external provider may become part of the kernel's architectural identity.**

This is the tool/capability equivalent of the Model Gateway.

## 131.2 Three-layer provider architecture

```text
JARVIS CODE
(agents / FSM / missions / effects)
        |
        v
CAPABILITY CONTRACT
stable, versioned, provider-agnostic
        |
        v
CAPABILITY REGISTRY
contract -> provider binding / policy / health / provenance
        |
        v
PROVIDER ADAPTER
JARVIS-owned translation + validation + error mapping
        |
        v
EXTERNAL PROVIDER
Browser Use / Playwright / Docling / MCP / etc.
```

The adapter belongs to JARVIS.

The provider does not call into the kernel directly.

Provider replacement must not require changing agents, missions, FSM states, memory semantics, or policy logic.

## 131.3 Capability contract

A capability contract describes semantic behavior, not implementation details.

Example:

```yaml
capability:
  contract_id: browser.navigate
  contract_version: 1.2.0
  description: Navigate to a URL and produce an observation of resulting page state
  inputs:
    url: string
    wait_until: enum
  outputs:
    page_state_ref: ArtifactRef
    status: enum
  required_capabilities:
    - NET_BROWSER
  trust_boundary: produces_untrusted_content
  verification:
    required: true
    method: observe_page_state
```

Breaking contract changes require a major version. Old contracts remain live until all dependent adapters migrate or are explicitly retired.

## 131.4 Provider registration

Every provider MUST carry supply-chain metadata.

```yaml
providers:
  - id: browser-use
    repo: <official repository reference>
    version: <pinned release>
    commit: <immutable commit SHA>
    license: MIT
    license_compatibility: approved
    adapter: jarvis.adapters.browser_use
    trust_level: sandboxed
    process_model: isolated_subprocess
    network: egress_only
    health_check: <provider-specific check>
    metrics_emitted:
      - latency
      - success_rate
      - provider_error_rate
    cve_status: checked
    last_audit: <UTC timestamp>
    provenance:
      added_by: <principal>
      added_at: <UTC timestamp>
      reason: <architectural justification>
    fallback: playwright
```

Registration MUST be blocked by CI or registry policy if required supply-chain fields are absent.

Minimum required provider metadata:

- provider identity
- repository/source provenance
- pinned version
- pinned commit/digest where applicable
- license
- license compatibility classification
- adapter identity
- trust/isolation level
- required network/filesystem scope
- CVE/security status
- last audit
- provenance of registration
- health-check definition
- fallback chain

A mutable tag such as `latest` is never an architectural pin.

## 131.5 Capability events

The registry is reconstructed from events such as:

```text
capability.registered
capability.provider_added
capability.provider_promoted
capability.provider_deprecated
capability.provider_revoked
capability.provider_health_changed
capability.resolved
capability.contract_versioned
capability.adapter_registered
```

`capability.resolved` records the runtime decision:

```text
contract
 + contract_version
 + mission/task context
 + policy context
 + resource state
 + selected provider
 + adapter version
 + reason
 + fallback position
```

This makes provider selection explainable and replayable.

## 131.6 Runtime resolution

At execution time:

```text
INTENT
  -> required semantic capability
  -> contract resolution
  -> policy / manifest validation
  -> provider health + circuit breaker
  -> resource / privacy / latency / cost checks
  -> provider selection
  -> JARVIS-owned adapter
  -> isolated provider
  -> EffectResult
  -> VERIFY
  -> event log
```

Provider choice is a routing decision, not application logic.

## 131.7 Mandatory invariants

1. No JARVIS kernel, agent, FSM, or mission code imports an external provider directly.
2. Every external call resolves through a versioned capability contract.
3. Every provider has supply-chain metadata.
4. Every provider is pinned to an immutable version/commit/digest where technically possible.
5. Every provider has a JARVIS-owned adapter.
6. Every provider executes outside the kernel process.
7. Every provider has a health check or an explicitly documented health strategy.
8. Every provider has a circuit breaker.
9. Every provider failure maps into the canonical `FailureKind` taxonomy.
10. Every contract has a fallback chain or explicitly records `unavailable` as its terminal fallback.
11. External content remains untrusted until independently validated.
12. Provider selection is recorded as provenance.
13. Provider replacement cannot require rewriting upstream cognitive logic.
14. Revoked providers cannot receive new work.
15. Provider registration cannot silently grant capabilities.

## 131.8 Capability versus tool versus skill

These concepts remain distinct:

```text
TOOL
  concrete mechanism

SKILL
  reusable executable procedure

CAPABILITY CONTRACT
  semantic ability exposed to JARVIS

PROVIDER
  implementation of that contract

ADAPTER
  JARVIS-owned translation boundary
```

Example:

```text
Browser Use
Playwright
        |
        +--> browser.navigate@1.2.0
        +--> browser.click@1.0.0
        +--> browser.observe@1.1.0

Software-debugging skill
        |
        +--> terminal.execute
        +--> filesystem.read/write
        +--> git operations
        +--> test execution
        +--> coding model
        +--> verification
```

The semantic capability is what the kernel reasons about.

## 131.9 Provider isolation

The preferred isolation hierarchy is:

```text
trusted in-process pure code
        |
isolated subprocess
        |
container
        |
VM
        |
TEE
        |
remote worker
```

The required level depends on trust, blast radius, privilege, data sensitivity, and physical impact.

No provider is allowed to execute arbitrary provider code inside the canonical kernel merely for convenience.

TEE is an optional stronger isolation tier, not a requirement for the first local implementation.

## 131.10 Model Gateway symmetry

The Model Gateway follows the same substitution-seam principle:

```text
MODEL ROLE CONTRACT
        |
MODEL REGISTRY
        |
MODEL ADAPTER
        |
MODEL PROVIDER / SERVING BACKEND
```

Therefore:

```text
CAPABILITY CONTRACT -> PROVIDER REGISTRY -> ADAPTER -> TOOL PROVIDER
MODEL ROLE CONTRACT -> MODEL REGISTRY -> ADAPTER -> MODEL PROVIDER
```

Both are instances of one architectural principle:

> **Stable semantic contracts above replaceable providers.**

## 131.11 LiteLLM placement

M1 decision: LiteLLM is the *routing implementation* behind the Model
Gateway interface.

```text
MODEL GATEWAY INTERFACE     ← JARVIS owns
  owns:
    routing policy declaration
    budget enforcement
    capability metadata
    provenance recording
    failover semantics
    model lifecycle events
        |
        v
LITELLM ADAPTER             ← JARVIS owns
        |
        v
LITELLM                     ← infrastructure
  provides:
    provider API translation
    provider key handling
    basic retry
        |
        v
model providers
```

JARVIS does not reimplement what LiteLLM already does well (provider
translation, key handling). JARVIS does reimplement what LiteLLM cannot own
(policy, budget, capability semantics, provenance).

Revisit at M3: if JARVIS routing needs grow beyond LiteLLM's model,
split the routing layer out of the adapter. Until then, LiteLLM is
infrastructure, not architecture.

vLLM is a serving backend, not the same abstraction as the model gateway.

## 131.12 Structured-output Model Fabric role

Schema-constrained generation is a first-class Model Fabric capability.

```text
SCHEMA_CONSTRAINED
  |
  +-- native backend constrained decoding
  +-- Outlines / equivalent
  +-- Instructor / Pydantic adapter
  +-- retry-on-validation-failure fallback
```

The Model Gateway records whether a backend provides native constrained decoding.

**M1 selection (ADR-006, ACCEPTED):** Pydantic v2 schema validation with retry-on-validation-failure is the M1 implementation; Ollama's native JSON-schema format is used behind the identical call when available. Outlines and other constrained-decoding backends remain future Model Gateway adapters. Frozen M1 interface: `generate_structured(role_contract, schema) -> ValidatedOutput | TypedFailure`.

The kernel never assumes that free-form model text is structurally valid.

Structured outputs remain versioned schemas validated before entering deterministic control paths.

## 131.13 Model Fabric roles expanded

Required semantic roles include:

```text
EXECUTE_REASONING
PLAN
CODE
CLASSIFY
VISION
STT
TTS
EMBED
RERANK
PII_DETECT
SCHEMA_CONSTRAINED
ROBOTICS_PERCEPTION
VLA/VLN
SIMULATION/WORLD_MODEL
SPECIALIST
```

Provider selection remains based on capability, quality, latency, cost, privacy, energy, thermal state, availability, and risk.

## 131.14 Embedding / reranking / privacy providers

The Memory OS may use replaceable providers for:

- embeddings: sentence-transformers or model-serving endpoints
- reranking: local or cloud rerankers
- PII detection: Presidio or equivalent

These are Model Fabric roles, not Memory OS identity.

Privacy-sensitive material SHOULD pass through PII detection/redaction/tagging before durable memory promotion according to policy.

A semantic retrieval index such as Qdrant remains an implementation detail behind the Memory API, never canonical truth.

## 131.15 Observability provider rule

Observability systems are subscribers, not kernel dependencies.

```text
JARVIS
  -> OpenTelemetry traces / metrics / logs
  -> optional OTLP collector
  -> Langfuse / Jaeger / Tempo / other backend
```

Langfuse must not sit on the critical execution path.

Evidently similarly consumes event/metric streams to compute drift and quality signals rather than becoming the source of truth.

If the observability backend disappears, JARVIS continues according to local observability/degraded-mode policy.

## 131.16 Evaluation boundary

Ragas is useful for RAG/final-answer quality dimensions but is not the canonical agent evaluator.

The Golden Task Harness evaluates trajectories directly from the event log:

- correct tool
- correct tool order
- valid arguments
- successful recovery
- cancellation behavior
- verification behavior
- evidence consistency
- final artifact correctness
- policy compliance
- resource budget compliance
- completion-gate correctness

LLM-as-judge metrics may supplement structural evaluation but cannot replace event-log-derived invariants.

## 131.17 Durable-execution research seam

Durable execution remains a replaceable infrastructure concern.

Temporal and Restate are tracked research candidates, not M1 dependencies.

The FSM MUST therefore preserve these properties:

1. state transitions are deterministic functions of state + event + validated artifact;
2. effects carry idempotency keys;
3. checkpoints occur at semantic recovery boundaries;
4. compensation is explicit;
5. canonical history remains append-only.

If these invariants hold, a future durable execution backend can replace the scheduler/execution substrate without changing the cognitive layer.

Research item:

```text
RESEARCH_BACKLOG:
  durable_execution_backend_comparison
  candidates: Temporal, Restate, equivalent open-source systems
  status: study_only
  trigger_for_adoption: measured recovery/scale requirement
```

## 131.18 External provider lifecycle

```text
DISCOVER
   ↓
SECURITY / LICENSE REVIEW
   ↓
CONTRACT MATCH
   ↓
ADAPTER IMPLEMENTATION
   ↓
SANDBOX TEST
   ↓
GOLDEN TASKS
   ↓
CANARY
   ↓
PROMOTE
   ↓
MONITOR
   ↓
DEPRECATE / REVOKE / REPLACE
```

Provider health and quality history feed routing, but trust/reputation never overrides hard safety policy.

## 131.19 Provider replacement proof

A provider replacement is successful only when the *lower-bound* guarantees
of the contract hold for the new provider.

### Contract = lower bound

A capability contract declares:

- input schema
- output schema
- required capabilities
- trust boundary
- verification method

It does *not* declare quality, latency, or behavioral richness beyond the
minimum. Two providers satisfying `browser.navigate@1.2.0` may differ in:
page-load fidelity, LLM-aware extraction, input precision, session handling.

### Adapter behavioral profile

Every adapter declares a `behavioral_profile` — a set of measurable
guarantees it can uphold. Examples:

```yaml
behavioral_profile:
  max_latency_ms: 2500
  min_success_rate: 0.95
  supports_sessions: true
  supports_llm_extraction: true
  supports_fine_input: false
```

### Callers may require more than the minimum

A mission or intent may declare `strict_contract: true` with additional
guarantees. The registry resolves only providers whose behavioral profile
satisfies the requirement.

If no provider qualifies:

- degrade explicitly (`capability.degraded`)
- or fail (`capability.unavailable`)
- or escalate to the creator

Never silently downgrade.

### Substitution proof

Substitution is proven by:

1. The contract id and version are unchanged.
2. The new adapter's behavioral profile meets the contract lower bound.
3. The new adapter's profile meets any `strict_contract` requirements
   declared by current callers.
4. Golden tasks pass.
5. Upstream mission, FSM, and policy definitions are unchanged.

If any caller's behavioral needs are not met, the substitution is *degraded*,
not successful. Degraded substitutions must be visible in
`capability.resolved` provenance.

## 131.20 Research and ecosystem governance

Every external repository considered for JARVIS must be treated as evidence-backed infrastructure, not automatically trusted because it is popular or impressive.

Evaluation must include:

- maintenance activity
- license
- security history
- dependency surface
- isolation requirements
- performance
- reproducibility
- community/production evidence
- compatibility with JARVIS contracts
- migration/replacement cost
- failure modes

Study competitor frameworks such as LangGraph, AutoGen, CrewAI, ElizaOS and similar systems for both successful patterns and documented failure modes.

The goal is not framework accumulation. The goal is architectural learning without dependency capture.

## 131.21 DECISION RECORD

**Decision: All external tools and models are accessed through versioned semantic contracts. No JARVIS code imports an external provider directly. Provider-specific behavior is isolated behind JARVIS-owned adapters and registry-controlled bindings.**

Rationale:

- preserves provider replacement
- limits supply-chain blast radius
- keeps architecture independent of ecosystem churn
- centralizes provenance and security metadata
- allows capability-level routing
- supports graceful fallback
- permits local/cloud/hardware providers to coexist
- prevents vendor-specific assumptions from leaking into cognitive logic

Status: **ACCEPTED / ARCHITECTURE INVARIANT**

---

# 132. FINAL INTEGRATION RULE

The External Capability Registry is not another subsystem competing with the kernel. It is the explicit boundary that makes the rest of the architecture replaceable.

The complete substitution hierarchy is:

```text
JARVIS COGNITIVE / EXECUTION LOGIC
              |
       semantic contracts
        /              \
MODEL ROLE CONTRACT   CAPABILITY CONTRACT
        |                     |
MODEL REGISTRY          CAPABILITY REGISTRY
        |                     |
MODEL ADAPTER           PROVIDER ADAPTER
        |                     |
MODEL PROVIDER          EXTERNAL PROVIDER
```

The kernel therefore owns:

```text
identity
intent
policy
authorization
orchestration
state
memory semantics
scheduling
verification
recovery
provenance
resource governance
```

while external systems provide replaceable capabilities:

```text
inference
retrieval
browser control
document parsing
vision
voice
coding workers
observability
evaluation
robotics
simulation
```

This separation is mandatory for the long-term JARVIS objective.

---

# 133. IMMEDIATE BUILD CONSEQUENCE

The next implementation step is NOT to install every repository.

The next implementation step is to build the seams first:

```text
M1
  Event Kernel
  + Identity
  + Deterministic FSM
  + Intent ABI
  + Capability Contract
  + Capability Registry
  + Provider Adapter Interface
  + Model Gateway
  + OpenTelemetry emission
  + Structured-output validation
  + first local model adapter
  + first simple capability adapter

M2
  Memory OS
  + PII detection seam
  + embedding seam
  + retrieval seam
  + memory verification
  + semantic checkpoints

M3
  Mission runtime
  + Saga
  + self-healing
  + agent capsules
  + Browser/Docling/coding capability adapters
  + golden trajectory evaluation

M4+
  phone / voice / vision / multi-agent community
  + A2A adapter
  + advanced isolation
  + coordination zones
  + always-on node

M5+
  robotics / VLA / digital twin
  + ROS2 / Gazebo / simulation adapters
  + physical safety plane

Future
  SNN / TEE / learned topology / market allocation /
  durable execution backend / self-development
  only when evidence requires them
```

**Architecture freeze remains in force:** adding a new external repository must not alter the kernel contract. It must enter through a contract, provider record, adapter, isolation policy, verification path, and supply-chain review.

---

# 134. M1 CUT LIST, NEGATIVE ACCEPTANCE TESTS, AND MILESTONE MAPPING

Added during the M1 readiness patch (SPEC_VERSION 1.0.0-freeze). Rationale and evidence: `docs/DECISIONS.md` ADR-005…009.

## 134.1 M1 cut list

MUST (the vertical slice):

- event store: SQLite WAL, hash-chained, append-only (ADR-005)
- creator identity + Ed25519 keypair (ADR-007)
- intent ABI + deterministic static validation
- capability registry seeded with 4 providers (filesystem, terminal, one local model adapter, HTTP client)
- provider adapter interface
- model gateway + first local adapter (Ollama)
- `generate_structured` (ADR-006)
- minimal memory projection (required by the §127.1 smoke test's `memory.write.*` flow — reconciliation, not scope creep)
- CLI: `init` / `say` / `explain`
- deterministic replay + `replay --verify`
- OpenTelemetry emission (`jarvis.*` spans)
- the five negative acceptance tests (§134.3)

STRETCH (M1.1):

- deterministic FSM (full mission lifecycle states)
- manifest DAG validation (full dependency-graph checks)
- full `jarvis explain` cause-chain rendering
- budget accounting display

EXCLUDED from M1:

- multi-agent runtime, agent capsules, sagas
- phone / voice / vision bodies
- external retrieval indexes (Qdrant et al.)
- robotics / simulation

## 134.2 M1 milestone ladder mapping

The M0–M5 ladder is canonical. Historical PHASE 0–13 references map as: PHASE 0 → M0/M1 scaffolding; 1–2 → M1; 3–4 → M3; 5–6 → M3/M4; 7 → M3; 8 → M4; 9 → M4+; 10 → M2/M3; 11 → M5; 12–13 → post-M5.

## 134.3 Negative acceptance tests (bind to §127.1)

| ID | Scenario | Required observable | Constitution clause |
|---|---|---|---|
| NAT-01 | model proposes a capability outside the granted set | `intent.rejected`; zero effects executed | 6, 11 |
| NAT-02 | non-creator principal emits `capability.provider_added` | authority rejection; registry unchanged | 5 |
| NAT-03 | replay the identical event log twice | byte-identical projection hashes | 20 |
| NAT-04 | tampered event row (payload/hash mismatch) | replay halts with typed integrity failure | 10 |
| NAT-05 | agent emits completion without the deterministic done-gate | refused; no completion event | 12 |
