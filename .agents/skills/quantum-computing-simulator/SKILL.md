---
name: quantum-computing-simulator
description: Enables JARVIS to simulate quantum circuits with qubits, apply quantum gates, run grover and shor algorithms, and visu.
---

# Quantum Computing Simulator Skill

## Purpose
Enables JARVIS to simulate quantum circuits with qubits, apply quantum gates, run grover and shor algorithms, and visu.

## When to Activate
Activate when the user asks to:
- perform quantum computing simulator
- help me simulate something
- automate quantum computing simulator
- quantum computing simulator task
- start quantum computing simulator

## Core Workflows

### 1. simulate quantum circuits with qubits, apply quantum gates, 
TODO: Implement the core workflow for this skill.

```python
# Add implementation here
# Connect to required services via JARVIS ProviderAdapter protocol
```

### 2. Error Handling
- Validate all inputs before execution.
- Catch and log all exceptions with descriptive messages.

## Prerequisites
None specified. Add required libraries and API keys here.

## Best Practices & Safety Invariants
- Verify all preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream `skill.quantum-computing-simulator`.
- Fail-closed with descriptive error messages.
- Never log raw secrets or PII into durable payloads.
- Adhere to the JARVIS External Capability Substitution Seam.
