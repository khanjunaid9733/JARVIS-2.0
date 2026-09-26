---
name: edu-citation-gen
description: Generate academic citations in APA, MLA, or Chicago style.
---

# Citation Generator Skill

## Purpose
Generate academic citations in APA, MLA, or Chicago style.

## When to Activate
Activate when the user asks to:
- citation
- reference format
- APA citation
- how to cite

## Core Workflows

Prompt: `Generate an {style} citation for: Author={author}, Title={title}, Year={year}, Source={source}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
