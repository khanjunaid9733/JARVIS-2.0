# J.A.R.V.I.S. 2.0

> **Persistent Autonomous Cognitive Operating System**  
> *Architected for PC, mobile, cloud, multimodal interaction, and robotics embodiment.*

---

## ⚡ Multi-Agent Development Protocol

This repository is developed cooperatively across three independent AI platforms. To maintain consistency without relying on ephemeral chat histories, **the repository itself is the single source of truth**.

| Platform | Agent / Persona | Assigned Role | Primary Duty |
| :--- | :--- | :--- | :--- |
| **OpenCode CLI** | *Big Pickle* | Primary Implementation | Implements code in `src/`, writes tests in `tests/`, executes CLI builds. |
| **Freebuff** | *DeepSeek* | Adversarial Architecture | Challenges designs, maps failure modes, proposes invariant tests. |
| **Antigravity IDE** | *Gemini* | Independent Reviewer | Audits filesystem/reality, inspects security boundaries, verifies quality. |

---

## 🧭 How to Start a Session as Any AI Agent

When opening this workspace in **any** tool (OpenCode, DeepSeek, Antigravity, Cursor, etc.), follow this protocol:

1. **Read [AGENTS.md](file:///f:/JARVIS2.0/AGENTS.md)**: Know your role and behavioral invariants.
2. **Read [DEVELOPMENT_CONTEXT.md](file:///f:/JARVIS2.0/DEVELOPMENT_CONTEXT.md)**: Understand what is accepted vs. proposed vs. forbidden.
3. **Inspect [project_state.yaml](file:///f:/JARVIS2.0/project_state.yaml)**: Check the current milestone and status flags.
4. **Inspect the actual disk**: Never assume code exists. If it is not in `src/`, it is not implemented.

---

## 📁 Repository Structure

```text
F:\JARVIS2.0\
├── AGENTS.md                    # Universal multi-agent behavioral rules & role contracts
├── DEVELOPMENT_CONTEXT.md       # High-level project briefing & accepted design invariants
├── project_state.yaml           # Machine-readable single source of truth
├── README.md                    # This document
├── .gitignore                   # Git exclusion rules
│
├── docs\
│   ├── MASTER_BUILD_SPEC.md     # Canonical 133-section engineering specification
│   ├── DECISIONS.md             # Formal Architecture Decision Records (ADRs)
│   ├── GLOSSARY.md              # Canonical terminology & system concepts
│   └── M0_AUDIT.md              # Host machine environment audit report
│
├── src\                         # Reserved for JARVIS runtime packages (M1+)
├── tests\                       # Reserved for automated unit & invariant tests
├── scripts\                     # Reserved for developer utilities & setup scripts
│
└── _archive\                    # Historical reference documents & prior conversation drafts
```

---

## 🚦 Current Status: `PRE_M0`

* **Runtime Code**: `NOT_STARTED`
* **M0 Environment Audit**: `IN_PROGRESS`
* **M1 Cognitive Kernel**: `NOT_STARTED`

See [DEVELOPMENT_CONTEXT.md](file:///f:/JARVIS2.0/DEVELOPMENT_CONTEXT.md) and [project_state.yaml](file:///f:/JARVIS2.0/project_state.yaml) for full details.
