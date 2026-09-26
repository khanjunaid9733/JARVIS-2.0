---
name: ds-feature-engineering
description: Create new features from existing data to improve model performance.
---

# Feature Engineering Skill

## Purpose
Create new features from existing data to improve model performance.

## When to Activate
Activate when the user asks to:
- feature engineering
- create features
- derive columns
- add features

## Core Workflows

Common: log transform, polynomial features, date decomposition, one-hot encoding.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
