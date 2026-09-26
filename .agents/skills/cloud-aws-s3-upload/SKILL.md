---
name: cloud-aws-s3-upload
description: Upload files to an AWS S3 bucket.
---

# AWS S3 File Upload Skill

## Purpose
Upload files to an AWS S3 bucket.

## When to Activate
Activate when the user asks to:
- upload to S3
- put file in S3
- S3 upload

## Core Workflows

```python
import boto3; boto3.client('s3').upload_file(file, bucket, key)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
