---
name: web-ip-geolocation
description: Get location, ISP, and country for any IP address.
---

# IP Geolocation Skill

## Purpose
Get location, ISP, and country for any IP address.

## When to Activate
Activate when the user asks to:
- where is IP <address>
- geolocate <ip>
- lookup IP

## Core Workflows

GET `https://ipapi.co/<IP>/json/`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
