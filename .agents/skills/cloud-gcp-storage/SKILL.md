---
name: cloud-gcp-storage
description: Upload and download files to Google Cloud Storage buckets.
---

# GCP Cloud Storage Skill

## Purpose
Upload and download files to Google Cloud Storage buckets.

## When to Activate
Activate when the user asks to:
- upload to GCS
- download from GCS
- GCP storage

## Core Workflows

```python
from google.cloud import storage; storage.Client().bucket(name).blob(key).upload_from_filename(path)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
