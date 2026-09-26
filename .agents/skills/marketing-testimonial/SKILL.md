---
name: marketing-testimonial
description: Write templates for requesting customer testimonials.
---

# Testimonial Request Writer Skill

## Purpose
Write templates for requesting customer testimonials.

## When to Activate
Activate when the user asks to:
- testimonial request
- ask for review
- customer review request

## Core Workflows

Prompt: `Write a concise, genuine testimonial request email for {product} asking {customer_type} for their experience.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
