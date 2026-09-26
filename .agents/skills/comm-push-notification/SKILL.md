---
name: comm-push-notification
description: Send push notifications to mobile devices via FCM or APNS.
---

# Push Notification Skill

## Purpose
Send push notifications to mobile devices via FCM or APNS.

## When to Activate
Activate when the user asks to:
- push notification
- send push
- notify phone

## Core Workflows

POST to `https://fcm.googleapis.com/fcm/send` with token and notification payload.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
