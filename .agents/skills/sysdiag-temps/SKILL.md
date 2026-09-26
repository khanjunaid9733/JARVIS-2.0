---
name: sysdiag-temps
description: Read CPU and GPU temperatures via hardware sensors.
---

# Hardware Temperature Skill

## Purpose
Read CPU and GPU temperatures via hardware sensors.

## When to Activate
Activate when the user asks to:
- CPU temperature
- how hot is my PC
- GPU temp

## Core Workflows

```python
psutil.sensors_temperatures()  # Linux; on Windows use OpenHardwareMonitor COM
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
