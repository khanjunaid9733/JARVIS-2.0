---
name: netadmin-nginx-config
description: Generate and validate nginx server configurations.
---

# Nginx Config Manager Skill

## Purpose
Generate and validate nginx server configurations.

## When to Activate
Activate when the user asks to:
- nginx config
- web server config
- reverse proxy
- nginx

## Core Workflows

Generate nginx server block with SSL, gzip, rate limiting, and security headers.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
