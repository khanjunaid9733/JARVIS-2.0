---
name: legal-compliance-checklist
description: Generate regulatory compliance checklists for HIPAA, SOC2, ISO27001.
---

# Compliance Checklist Skill

## Purpose
Generate regulatory compliance checklists for HIPAA, SOC2, ISO27001.

## When to Activate
Activate when the user asks to:
- compliance checklist
- HIPAA
- SOC2
- ISO27001
- regulatory

## Core Workflows

Prompt: `Create a compliance checklist for {standard} relevant to a {company_type}. Include controls and evidence.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
