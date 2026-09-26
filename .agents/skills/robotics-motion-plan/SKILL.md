---
name: robotics-motion-plan
description: Plan collision-free paths for robot arms or mobile robots.
---

# Robot Motion Planner Skill

## Purpose
Plan collision-free paths for robot arms or mobile robots.

## When to Activate
Activate when the user asks to:
- motion planning
- robot path
- trajectory
- robot move

## Core Workflows

Use RRT or A* algorithm on occupancy grid. Return waypoint sequence.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
