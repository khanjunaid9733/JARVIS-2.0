---
name: robotics-pwm
description: Control servo motors and DC motors via PWM signals.
---

# PWM Motor Controller Skill

## Purpose
Control servo motors and DC motors via PWM signals.

## When to Activate
Activate when the user asks to:
- servo control
- motor speed
- PWM
- rotate servo

## Core Workflows

```python
pwm = GPIO.PWM(pin, 50)  # 50Hz; pwm.ChangeDutyCycle(7.5)  # 90 degrees
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
