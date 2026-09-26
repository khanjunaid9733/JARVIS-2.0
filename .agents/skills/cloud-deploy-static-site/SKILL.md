---
name: cloud-deploy-static-site
description: Deploy a static website to S3+CloudFront or Firebase Hosting.
---

# Static Site Deploy Skill

## Purpose
Deploy a static website to S3+CloudFront or Firebase Hosting.

## When to Activate
Activate when the user asks to:
- deploy website
- publish static site
- push to hosting

## Core Workflows

```bash
aws s3 sync ./dist s3://<bucket>/ --delete
aws cloudfront create-invalidation --paths '/*'
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
