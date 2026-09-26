---
name: cloud-secrets-manager
description: Fetch secrets from AWS Secrets Manager or GCP Secret Manager.
---

# Cloud Secrets Retrieval Skill

## Purpose
Fetch secrets from AWS Secrets Manager or GCP Secret Manager.

## When to Activate
Activate when the user asks to:
- get secret from AWS
- retrieve cloud secret
- secrets manager

## Core Workflows

```python
boto3.client('secretsmanager').get_secret_value(SecretId=name)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
