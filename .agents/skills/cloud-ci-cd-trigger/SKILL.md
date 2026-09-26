---
name: cloud-ci-cd-trigger
description: Trigger GitHub Actions, GitLab CI, or Jenkins pipelines.
---

# CI/CD Pipeline Trigger Skill

## Purpose
Trigger GitHub Actions, GitLab CI, or Jenkins pipelines.

## When to Activate
Activate when the user asks to:
- trigger CI
- run pipeline
- deploy pipeline

## Core Workflows

POST to GitHub API `/repos/<owner>/<repo>/actions/workflows/<id>/dispatches`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
