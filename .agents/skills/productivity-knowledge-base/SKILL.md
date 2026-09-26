---
name: productivity-knowledge-base
description: Build and query a searchable knowledge base from notes and documents.
---

# Personal Knowledge Base Skill

## Purpose
Build and query a searchable knowledge base from notes and documents.

## When to Activate
Activate when the user asks to:
- search knowledge base
- add to KB
- knowledge base query

## Core Workflows

Index documents with embeddings, use vector similarity search for retrieval.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
