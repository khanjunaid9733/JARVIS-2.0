---
name: science-genetics
description: Explain genes, codons, mutations, and inheritance patterns.
---

# Genetics Assistant Skill

## Purpose
Explain genes, codons, mutations, and inheritance patterns.

## When to Activate
Activate when the user asks to:
- genetics
- DNA sequence
- codon
- gene mutation
- inheritance

## Core Workflows

Prompt: `Explain {genetics topic} with specific molecular details and examples.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
