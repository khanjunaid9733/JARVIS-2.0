---
name: cloud-aws-ec2-status
description: Check status, type, and public IP of EC2 instances.
---

# AWS EC2 Instance Status Skill

## Purpose
Check status, type, and public IP of EC2 instances.

## When to Activate
Activate when the user asks to:
- EC2 status
- instance running
- list EC2

## Core Workflows

```python
boto3.client('ec2').describe_instances()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
