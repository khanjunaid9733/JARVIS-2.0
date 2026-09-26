---
name: marketing-utm-builder
description: Build UTM tracking URLs for campaign analytics.
---

# UTM Parameter Builder Skill

## Purpose
Build UTM tracking URLs for campaign analytics.

## When to Activate
Activate when the user asks to:
- UTM link
- tracking URL
- campaign URL
- UTM parameters

## Core Workflows

Construct: `url?utm_source=<>&utm_medium=<>&utm_campaign=<>&utm_content=<>`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
