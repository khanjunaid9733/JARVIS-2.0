---
name: legal-EULA
description: Generate End User License Agreements for software products.
---

# EULA Generator Skill

## Purpose
Generate End User License Agreements for software products.

## When to Activate
Activate when the user asks to:
- EULA
- software license
- end user license
- license agreement

## Core Workflows

Prompt: `Draft an EULA for {software} covering: scope, restrictions, warranties, termination, governing law.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
