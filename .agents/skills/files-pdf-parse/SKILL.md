---
name: files-pdf-parse
description: Extract and search text content from PDF files.
---

# PDF Text Extractor Skill

## Purpose
Extract and search text content from PDF files.

## When to Activate
Activate when the user asks to:
- read PDF
- extract text from PDF
- parse PDF

## Core Workflows

Use `pypdf` or `pdfminer.six`: `PdfReader(path).pages[0].extract_text()`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
