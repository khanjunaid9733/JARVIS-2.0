---
name: smarthome-automations-list
description: List all active Home Assistant automations and their triggers.
---

# List Active Automations Skill

## Purpose
List all active Home Assistant automations and their triggers.

## When to Activate
Activate when the user asks to:
- list automations
- show HA automations
- what automations are running

## Core Workflows

GET `http://<HA_HOST>/api/automations` and return all active automations.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
