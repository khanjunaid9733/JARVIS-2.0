---
name: social-profile-bio
description: Write compelling social media bios and profile descriptions.
---

# Social Media Bio Writer Skill

## Purpose
Write compelling social media bios and profile descriptions.

## When to Activate
Activate when the user asks to:
- write bio
- profile description
- Twitter bio
- LinkedIn summary

## Core Workflows

Prompt: `Write a compelling {platform} bio for someone who is a {role} with expertise in {skills}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
