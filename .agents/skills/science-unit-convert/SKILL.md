---
name: science-unit-convert
description: Convert between any scientific units (length, mass, energy, temperature).
---

# Unit Converter Skill

## Purpose
Convert between any scientific units (length, mass, energy, temperature).

## When to Activate
Activate when the user asks to:
- convert <unit>
- unit conversion
- meters to feet
- Celsius to Fahrenheit

## Core Workflows

```python
import pint; ureg = pint.UnitRegistry(); (5 * ureg.meter).to('foot')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
