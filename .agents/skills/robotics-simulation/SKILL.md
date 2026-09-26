---
name: robotics-simulation
description: Simulate robot behavior in Gazebo or PyBullet.
---

# Robot Simulation Skill

## Purpose
Simulate robot behavior in Gazebo or PyBullet.

## When to Activate
Activate when the user asks to:
- robot simulation
- simulate in Gazebo
- PyBullet
- virtual robot

## Core Workflows

```python
import pybullet as p; p.connect(p.GUI); p.loadURDF('robot.urdf')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
