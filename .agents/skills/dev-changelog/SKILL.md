---
name: dev-changelog
description: Auto-generate a CHANGELOG from git commit messages.
---

# Changelog Generator Skill

## Purpose
Auto-generate a CHANGELOG from git commit messages.

## When to Activate
Activate when the user asks to:
- generate changelog
- create release notes
- git changelog

## Core Workflows

Parse `git log --oneline` and group commits by type (feat, fix, docs).

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
