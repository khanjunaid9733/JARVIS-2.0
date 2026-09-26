---
name: db-data-quality
description: Run null count, duplicate detection, and distribution checks on tables.
---

# Data Quality Checker Skill

## Purpose
Run null count, duplicate detection, and distribution checks on tables.

## When to Activate
Activate when the user asks to:
- data quality
- check for nulls
- duplicates in table

## Core Workflows

Run `SELECT COUNT(*), COUNT(col), COUNT(DISTINCT col) FROM table GROUP BY ...`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
