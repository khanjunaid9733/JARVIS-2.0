---
name: media-spotify-play
description: Play, pause, skip, and queue tracks on Spotify.
---

# Spotify Playback Control Skill

## Purpose
Play, pause, skip, and queue tracks on Spotify.

## When to Activate
Activate when the user asks to:
- play <song>
- pause Spotify
- next track
- queue <song>

## Core Workflows

Use Spotify Web API: PUT `/me/player/play` with context_uri or track URIs.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
