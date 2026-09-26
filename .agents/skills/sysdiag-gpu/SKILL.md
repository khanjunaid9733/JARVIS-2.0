---
name: sysdiag-gpu
description: Query GPU utilization, VRAM usage, and driver version.
---

# GPU Status Skill

## Purpose
Query GPU utilization, VRAM usage, and driver version.

## When to Activate
Activate when the user asks to:
- GPU usage
- VRAM
- graphics card status

## Core Workflows

Run `nvidia-smi` or `wmic path win32_videocontroller get name,adapterram`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
