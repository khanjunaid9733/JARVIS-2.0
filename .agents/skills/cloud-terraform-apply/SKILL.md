---
name: cloud-terraform-apply
description: Plan and apply Terraform infrastructure changes.
---

# Terraform Infra Apply Skill

## Purpose
Plan and apply Terraform infrastructure changes.

## When to Activate
Activate when the user asks to:
- terraform apply
- deploy infra
- provision cloud resources

## Core Workflows

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
