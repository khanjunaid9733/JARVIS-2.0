---
name: security-audit-log
description: View JARVIS event log for unauthorized access attempts or anomalies.
---

# Access Audit Log Skill

## Purpose
View JARVIS event log for unauthorized access attempts or anomalies.

## When to Activate
Activate when the user asks to:
- audit log
- security events
- access log
- suspicious activity

## Core Workflows

Query JARVIS EventLog for `auth.failed`, `capability.denied` stream events.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
