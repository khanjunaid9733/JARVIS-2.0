---
name: codegen-cicd-pipeline
description: Generate GitHub Actions, GitLab CI, or Jenkins pipeline configs.
---

# CI/CD Pipeline Config Skill

## Purpose
Generate GitHub Actions, GitLab CI, or Jenkins pipeline configs.

## When to Activate
Activate when the user asks to:
- GitHub Actions
- GitLab CI
- CI pipeline
- CD pipeline

## Core Workflows

Generate: workflow YAML with build, test, lint, security scan, and deploy stages.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
