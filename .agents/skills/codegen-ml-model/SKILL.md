---
name: codegen-ml-model
description: Generate scikit-learn or PyTorch model training code.
---

# ML Model Code Generator Skill

## Purpose
Generate scikit-learn or PyTorch model training code.

## When to Activate
Activate when the user asks to:
- ML model code
- train model code
- deep learning code
- neural network

## Core Workflows

Generate: data loading, preprocessing, model definition, training loop, evaluation.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
