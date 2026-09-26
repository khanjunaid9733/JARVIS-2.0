---
name: robotics-firmware-flash
description: Flash firmware to Arduino or ESP32 microcontrollers.
---

# Firmware Flasher Skill

## Purpose
Flash firmware to Arduino or ESP32 microcontrollers.

## When to Activate
Activate when the user asks to:
- flash Arduino
- upload firmware
- Arduino upload
- ESP32 flash

## Core Workflows

```bash
avrdude -p atmega328p -c arduino -P COM3 -b 115200 -U flash:w:firmware.hex
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
