---
name: blockchain-whitepaper
description: Download and summarize any cryptocurrency whitepaper.
---

# Crypto Whitepaper Summarizer Skill

## Purpose
Download and summarize any cryptocurrency whitepaper.

## When to Activate
Activate when the user asks to:
- whitepaper
- explain <coin>
- summarize crypto paper

## Core Workflows

Download whitepaper PDF, extract text, route through LLM for summary.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
