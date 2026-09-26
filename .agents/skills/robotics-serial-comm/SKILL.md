---
name: robotics-serial-comm
description: Send and receive data over UART serial ports.
---

# Serial Communication Skill

## Purpose
Send and receive data over UART serial ports.

## When to Activate
Activate when the user asks to:
- serial port
- UART
- Arduino communication
- serial send

## Core Workflows

```python
import serial; ser = serial.Serial('/dev/ttyUSB0', 9600); ser.write(b'data')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
