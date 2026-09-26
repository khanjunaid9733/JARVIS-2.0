---
name: browser-monitor-price
description: Monitor a product price on a website and alert on drop.
---

# Price Monitor Skill

## Purpose
Monitor a product price on a website and alert on drop.

## When to Activate
Activate when the user asks to:
- monitor price
- price alert <url>
- track price
- alert when price drops

## Core Workflows

Poll page selector every 30 min, compare to stored price, alert on decrease.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
