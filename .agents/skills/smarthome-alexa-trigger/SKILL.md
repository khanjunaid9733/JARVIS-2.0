---
name: smarthome-alexa-trigger
description: Trigger Amazon Alexa routines via custom voice or API command.
---

# Alexa Routine Trigger Skill

## Purpose
Trigger Amazon Alexa routines via custom voice or API command.

## When to Activate
Activate when the user asks to:
- trigger Alexa routine
- Alexa <routine>

## Core Workflows

Use Alexa Remote Control (alexa-remote2) or n8n Alexa workflow.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
