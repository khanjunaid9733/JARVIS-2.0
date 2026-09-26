---
name: security-vpn-status
description: Check if the VPN is active and which country the IP routes through.
---

# VPN Status Checker Skill

## Purpose
Check if the VPN is active and which country the IP routes through.

## When to Activate
Activate when the user asks to:
- VPN status
- am I on VPN
- is VPN on
- check VPN

## Core Workflows

Compare public IP (ipapi.co) vs known VPN ranges or check WireGuard/OpenVPN status.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
