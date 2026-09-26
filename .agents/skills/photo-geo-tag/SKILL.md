---
name: photo-geo-tag
description: Add or read GPS location data from photo EXIF tags.
---

# Photo Geo-Tagger Skill

## Purpose
Add or read GPS location data from photo EXIF tags.

## When to Activate
Activate when the user asks to:
- GPS location of photo
- where was photo taken
- geo-tag image

## Core Workflows

Read EXIF GPSInfo tag, convert to decimal degrees. Write with `piexif.dump()`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
