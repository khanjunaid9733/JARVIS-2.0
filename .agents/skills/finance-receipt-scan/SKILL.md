---
name: finance-receipt-scan
description: Extract merchant, date, and amount from receipt images using OCR.
---

# Receipt Scanner Skill

## Purpose
Extract merchant, date, and amount from receipt images using OCR.

## When to Activate
Activate when the user asks to:
- scan receipt
- receipt photo
- extract receipt

## Core Workflows

Use Tesseract OCR + LLM to extract structured data from receipt image.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
