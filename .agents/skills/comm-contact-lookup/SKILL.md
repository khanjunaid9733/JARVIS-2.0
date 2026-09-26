---
name: comm-contact-lookup
description: Find and display contact information from a local or cloud address book.
---

# Contact Lookup Skill

## Purpose
Find and display contact information from a local or cloud address book.

## When to Activate
Activate when the user asks to:
- find contact
- look up <name>
- contact info for

## Core Workflows

Query Google People API or local vCard files.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
