---
name: robotics-gpio-write
description: Write digital HIGH/LOW signals to GPIO pins on Raspberry Pi.
---

# GPIO Pin Writer Skill

## Purpose
Write digital HIGH/LOW signals to GPIO pins on Raspberry Pi.

## When to Activate
Activate when the user asks to:
- GPIO write
- set pin HIGH
- LED on
- digital output

## Core Workflows

```python
import RPi.GPIO as GPIO; GPIO.output(pin, GPIO.HIGH)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
