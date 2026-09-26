---
name: edu-scientific-method
description: Guide users through designing experiments with scientific method.
---

# Scientific Method Guide Skill

## Purpose
Guide users through designing experiments with scientific method.

## When to Activate
Activate when the user asks to:
- scientific experiment
- hypothesis
- experimental design
- methodology

## Core Workflows

Step through: Observation → Hypothesis → Experiment Design → Data → Analysis → Conclusion.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
