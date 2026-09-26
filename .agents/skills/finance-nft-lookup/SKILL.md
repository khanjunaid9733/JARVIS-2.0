---
name: finance-nft-lookup
description: Fetch metadata, owner, and sale history of an NFT.
---

# NFT Lookup Skill

## Purpose
Fetch metadata, owner, and sale history of an NFT.

## When to Activate
Activate when the user asks to:
- NFT info
- look up NFT
- token metadata

## Core Workflows

GET OpenSea API `/api/v1/asset/<contract>/<token_id>/`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
