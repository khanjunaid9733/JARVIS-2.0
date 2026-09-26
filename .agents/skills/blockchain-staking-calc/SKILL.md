---
name: blockchain-staking-calc
description: Calculate expected staking rewards for any PoS asset.
---

# Staking Reward Calculator Skill

## Purpose
Calculate expected staking rewards for any PoS asset.

## When to Activate
Activate when the user asks to:
- staking rewards
- staking APY
- staking calculator
- earn from staking

## Core Workflows

reward = stake × APY × days/365. Account for commission if applicable.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
