---
name: robotics-ros-publish
description: Publish messages to ROS topics.
---

# ROS Topic Publisher Skill

## Purpose
Publish messages to ROS topics.

## When to Activate
Activate when the user asks to:
- ROS publish
- robot topic
- ROS message
- publish to topic

## Core Workflows

```python
import rospy; pub = rospy.Publisher('/topic', String, queue_size=10); pub.publish(msg)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
