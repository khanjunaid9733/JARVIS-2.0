---
name: productivity-invoice
description: Create professional PDF invoices from time tracking data.
---

# Invoice Generator Skill

## Purpose
Create professional PDF invoices from time tracking data.

## When to Activate
Activate when the user asks to:
- create invoice
- generate bill
- invoice client

## Core Workflows

Use ReportLab or FPDF to generate a PDF invoice from tracked hours × rate.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
