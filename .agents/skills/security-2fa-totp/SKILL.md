---
name: security-2fa-totp
description: Generate TOTP two-factor authentication codes.
---

# TOTP Code Generator Skill

## Purpose
Generate TOTP two-factor authentication codes.

## When to Activate
Activate when the user asks to:
- generate 2FA code
- TOTP code for
- OTP code

## Core Workflows

```python
import pyotp; pyotp.TOTP('<base32_secret>').now()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
