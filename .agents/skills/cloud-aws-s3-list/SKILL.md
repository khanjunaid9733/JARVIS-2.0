---
name: cloud-aws-s3-list
description: List files in an S3 bucket with size and last-modified.
---

# AWS S3 Bucket Lister Skill

## Purpose
List files in an S3 bucket with size and last-modified.

## When to Activate
Activate when the user asks to:
- list S3 bucket
- what's in S3
- S3 files

## Core Workflows

```python
boto3.client('s3').list_objects_v2(Bucket=bucket)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
