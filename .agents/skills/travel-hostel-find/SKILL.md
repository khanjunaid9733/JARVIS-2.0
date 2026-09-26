---
name: travel-hostel-find
description: Find budget hostels and guesthouses in any city.
---

# Hostel & Budget Stay Finder Skill

## Purpose
Find budget hostels and guesthouses in any city.

## When to Activate
Activate when the user asks to:
- cheap stay
- hostel in
- budget hotel
- affordable accommodation

## Core Workflows

Use HostelWorld API or Booking.com with price filter applied.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
