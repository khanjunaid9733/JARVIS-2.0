---
name: writing-blog
description: Write SEO-optimized blog posts with headings and meta description.
---

# Blog Post Writer Skill

## Purpose
Write SEO-optimized blog posts with headings and meta description.

## When to Activate
Activate when the user asks to:
- write blog post
- blog article
- content about
- blog on

## Core Workflows

Prompt: `Write a {word_count}-word blog post titled '{title}' optimized for '{keyword}' with H2 subheadings.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
