---
name: social-unfollower-detector
description: Detect accounts that unfollowed you on Twitter or Instagram.
---

# Unfollower Detector Skill

## Purpose
Detect accounts that unfollowed you on Twitter or Instagram.

## When to Activate
Activate when the user asks to:
- who unfollowed me
- unfollower check
- lost followers

## Core Workflows

Store previous follower list snapshot, compare with current followers list.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
