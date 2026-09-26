---
name: finance-invoice-parse
description: Extract amount, vendor, date, and line items from invoice files.
---

# Invoice Parser Skill

## Purpose
Extract amount, vendor, date, and line items from invoice files.

## When to Activate
Activate when the user asks to:
- parse invoice
- extract from invoice
- invoice OCR

## Core Workflows

Use LLM or pdfminer to extract structured data from invoice PDF/image.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
