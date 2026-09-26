---
name: blockchain-wallet-balance
description: Check ETH, BTC, or ERC-20 token balances for any wallet address.
---

# Wallet Balance Checker Skill

## Purpose
Check ETH, BTC, or ERC-20 token balances for any wallet address.

## When to Activate
Activate when the user asks to:
- wallet balance
- ETH balance
- how much in wallet
- token balance

## Core Workflows

GET Etherscan API `?module=account&action=balance&address=<addr>&tag=latest`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
