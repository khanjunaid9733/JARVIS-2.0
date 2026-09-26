---
name: assistant-appointment-book
description: Schedule appointments and send calendar invites.
---

# Appointment Booker Skill

## Purpose
Schedule appointments and send calendar invites.

## When to Activate
Activate when the user asks to:
- book appointment
- schedule meeting
- set up call
- arrange time

## Core Workflows

Create Google Calendar event, send email invitations with Meet link.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
