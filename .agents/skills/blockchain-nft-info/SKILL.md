---
name: blockchain-nft-info
description: Retrieve NFT metadata, image, and traits from OpenSea.
---

# NFT Metadata Fetcher Skill

## Purpose
Retrieve NFT metadata, image, and traits from OpenSea.

## When to Activate
Activate when the user asks to:
- NFT info
- NFT metadata
- look up NFT
- token traits

## Core Workflows

GET OpenSea API `/api/v1/asset/<contract>/<token_id>/`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
