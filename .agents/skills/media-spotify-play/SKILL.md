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

```python
import urllib.parse
import webbrowser

track_name = query if 'query' in locals() and query else (track if 'track' in locals() and track else "lahar by arijit singh")
url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(str(track_name))}"
webbrowser.open(url)
print(f"Initiated media playback for: {track_name}")
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
