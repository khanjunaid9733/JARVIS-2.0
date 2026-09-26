---
name: photo-batch-rename
description: Rename photos in bulk by date, sequence, or custom pattern.
---

# Batch Photo Renamer Skill

## Purpose
Rename photos in bulk by date, sequence, or custom pattern.

## When to Activate
Activate when the user asks to:
- rename photos
- batch rename
- organize photos
- rename by date

## Core Workflows

Sort by EXIF date, rename to pattern: `YYYY-MM-DD_HHmmss_N.ext`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
