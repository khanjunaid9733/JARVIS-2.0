---
name: health-cycle-track
description: Track menstrual cycles and predict next period and fertile window.
---

# Menstrual Cycle Tracker Skill

## Purpose
Track menstrual cycles and predict next period and fertile window.

## When to Activate
Activate when the user asks to:
- period tracker
- cycle tracking
- fertile window
- next period

## Core Workflows

Store cycle dates, compute average length, predict next cycle start.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
