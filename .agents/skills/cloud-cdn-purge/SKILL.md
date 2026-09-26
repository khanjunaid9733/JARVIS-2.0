---
name: cloud-cdn-purge
description: Purge specific URLs from Cloudflare or CloudFront CDN.
---

# CDN Cache Purge Skill

## Purpose
Purge specific URLs from Cloudflare or CloudFront CDN.

## When to Activate
Activate when the user asks to:
- purge CDN
- clear cache
- CDN invalidate

## Core Workflows

POST to Cloudflare API `/zones/<zone>/purge_cache` with URLs array.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
