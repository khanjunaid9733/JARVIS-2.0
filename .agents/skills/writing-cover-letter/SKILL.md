---
name: writing-cover-letter
description: Write professional cover letters tailored to job descriptions.
---

# Cover Letter Writer Skill

## Purpose
Write professional cover letters tailored to job descriptions.

## When to Activate
Activate when the user asks to:
- cover letter
- job application letter
- write cover letter for

## Core Workflows

Prompt: `Write a cover letter for a {role} at {company}. Skills: {skills}. Background: {background}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
