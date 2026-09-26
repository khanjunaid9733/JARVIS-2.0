---
name: robotics-i2c-sensor
description: Read data from I2C-connected sensors (BME280, MPU6050, etc.).
---

# I2C Sensor Reader Skill

## Purpose
Read data from I2C-connected sensors (BME280, MPU6050, etc.).

## When to Activate
Activate when the user asks to:
- I2C sensor
- temperature sensor
- gyroscope
- accelerometer

## Core Workflows

```python
import smbus; bus = smbus.SMBus(1); bus.read_byte_data(addr, reg)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
