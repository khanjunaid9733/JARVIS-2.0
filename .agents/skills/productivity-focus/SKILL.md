---
name: productivity-focus
description: Block distracting websites and apps during work sessions.
---

# Focus Mode Skill

## Purpose
Block distracting websites and apps during work sessions.

## When to Activate
Activate when the user asks to:
- focus mode
- block distractions
- block social media
- work mode

## Core Workflows

Modify Windows HOSTS file to redirect distraction domains to 127.0.0.1 during session.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
