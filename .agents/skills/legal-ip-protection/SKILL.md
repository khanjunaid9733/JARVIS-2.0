---
name: legal-ip-protection
description: Guide creators on protecting intellectual property.
---

# IP Protection Guide Skill

## Purpose
Guide creators on protecting intellectual property.

## When to Activate
Activate when the user asks to:
- protect IP
- copyright
- intellectual property
- patent my idea

## Core Workflows

Prompt: `Advise on protecting {ip_type} for {creation}. Explain: copyright, trademark, patent options and steps.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
