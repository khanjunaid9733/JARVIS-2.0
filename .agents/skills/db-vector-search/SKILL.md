---
name: db-vector-search
description: Perform semantic similarity search using a vector database.
---

# Vector Similarity Search Skill

## Purpose
Perform semantic similarity search using a vector database.

## When to Activate
Activate when the user asks to:
- semantic search
- similarity search
- find similar
- vector search

## Core Workflows

Use ChromaDB or Qdrant: `collection.query(query_embeddings=..., n_results=5)`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
