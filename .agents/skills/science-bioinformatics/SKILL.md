---
name: science-bioinformatics
description: Analyze DNA/protein sequences and run alignment or annotation.
---

# Bioinformatics Assistant Skill

## Purpose
Analyze DNA/protein sequences and run alignment or annotation.

## When to Activate
Activate when the user asks to:
- DNA sequence
- protein sequence
- BLAST
- bioinformatics
- sequence alignment

## Core Workflows

Use Biopython: `SeqIO.parse()`, `pairwise2.align()`, NCBI Entrez API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
