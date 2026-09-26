---
name: netadmin-fail2ban
description: Configure fail2ban to block brute-force attacks.
---

# Fail2Ban Configuration Skill

## Purpose
Configure fail2ban to block brute-force attacks.

## When to Activate
Activate when the user asks to:
- fail2ban
- block brute force
- SSH protection
- IP banning

## Core Workflows

Generate jail.local config for SSH, nginx, and application-specific filters.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
