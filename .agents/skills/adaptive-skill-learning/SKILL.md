---
name: adaptive-skill-learning
description: Autonomous meta-skill protocol enabling JARVIS to dynamically learn, synthesize, generate, and persist new skills on-the-fly based on user demands and real-time operational requirements.
---

# Adaptive Skill Learning & Creation Protocol

## Purpose
Enables JARVIS 2.0 to be self-evolving and continuously adaptive. When a creator or user requests a task, workflow, or capability that is not yet part of the standard skill library, JARVIS autonomously synthesizes, validates, and commits a new skill into `.agents/skills/<skill-name>/SKILL.md` and records it into durable memory.

## When to Activate
Activate this skill whenever:
- The user requests a new skill, capability, or automation that JARVIS does not currently support.
- A mission requires an unrepresented domain capability (e.g. specialized API, hardware protocol, external service).
- The user explicitly instructs: "teach yourself a new skill", "learn how to do X", or "create an automation for Y".

## The 5-Stage Adaptive Learning Pipeline

```text
  [1. Ingest Demand] ──> [2. Capability Mapping] ──> [3. Synthesize Skill Spec]
                                                                │
  [5. Durable Memory Commit] <── [4. Materialize & Verify] <────┘
```

### Stage 1: Ingest Demand
- Extract the core goal, required inputs, preconditions, expected outputs, and constraints from the user's prompt.
- Identify whether the task requires:
  1. **n8n Workflow Automation**: For multi-service APIs, webhooks, or third-party web apps (Spotify, Slack, Notion, Gmail, etc.).
  2. **Local OS / Headless Scripting**: For Windows/Linux CLI tools, file conversions, process control, or PowerShell commands.
  3. **HTN Domain Method / Operator**: For complex multi-step mission decompositions.

### Stage 2: Capability & Bridge Mapping
- Determine if an existing adapter satisfies the demand (e.g., `N8nWorkflowAdapter`, `PeripheralAdapter`, `FilesystemEffectAdapter`, `ComputerUseAdapter`).
- If an external cloud service is needed, configure or generate an n8n webhook or workflow node pipeline.

### Stage 3: Synthesize Skill Specification
Generate the new skill following the Antigravity/JARVIS standard in `.agents/skills/<skill-name>/SKILL.md`:
```markdown
---
name: <kebab-case-skill-name>
description: <concise summary of capability and triggers>
---

# <Skill Title>

## Purpose
<Why this skill exists and what problems it solves>

## When to Activate
<Trigger phrases and conditions>

## Core Workflows
<Step-by-step procedures, code snippets, and commands>

## Best Practices & Safety Invariants
<Precondition checks, error handling, security considerations>
```

### Stage 4: Materialize & Verify
1. Create directory: `.agents/skills/<skill-name>/`
2. Write `SKILL.md` (and any necessary helper scripts/templates in subdirectories).
3. Verify that the YAML frontmatter is valid and all file references exist.

### Stage 5: Commit to Durable Memory
Record the newly acquired skill into JARVIS's persistent memory ledger:
```bash
jarvis say "remember: [Skill Acquired] <skill-name>: <short summary of what was learned and how to trigger it>"
```
This guarantees that after restarts or context resets, JARVIS immediately recalls that the skill exists and how to use it.

## Best Practices & Safety Invariants
- **Non-Destructive**: Never overwrite or delete existing verified skills without explicit creator approval.
- **Fail-Closed Verification**: If dependencies or API credentials are required, clearly declare them in the skill's Prerequisites section before claiming operational readiness.
- **Durable Provenance**: Always stamp the skill acquisition event into the hash-chained SQLite event log.
