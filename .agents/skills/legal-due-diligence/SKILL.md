---
name: legal-due-diligence
description: Create due diligence checklists for mergers and acquisitions.
---

# M&A Due Diligence Checklist Skill

## Purpose
Create due diligence checklists for mergers and acquisitions.

## When to Activate
Activate when the user asks to:
- due diligence
- M&A checklist
- acquisition review
- legal due diligence

## Core Workflows

Prompt: `Create a due diligence checklist for acquiring {company_type}. Cover: financial, legal, technical, HR, IP.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
