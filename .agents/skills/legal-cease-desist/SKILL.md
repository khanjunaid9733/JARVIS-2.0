---
name: legal-cease-desist
description: Draft cease and desist letters for IP or trademark infringement.
---

# Cease & Desist Letter Skill

## Purpose
Draft cease and desist letters for IP or trademark infringement.

## When to Activate
Activate when the user asks to:
- cease and desist
- copyright infringement letter
- stop using
- IP violation

## Core Workflows

Prompt: `Draft a cease and desist letter from {sender} to {recipient} regarding {infringement}. Professional and firm tone.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
