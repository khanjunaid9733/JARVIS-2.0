---
name: robotics-gpio-read
description: Read digital or analog values from GPIO input pins.
---

# GPIO Pin Reader Skill

## Purpose
Read digital or analog values from GPIO input pins.

## When to Activate
Activate when the user asks to:
- GPIO read
- read sensor
- pin state
- digital input

## Core Workflows

```python
GPIO.input(pin)  # returns 0 or 1
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
