---
name: media-movie-info
description: Fetch movie details, ratings, cast, and trailers from OMDB/TMDB.
---

# Movie Info Lookup Skill

## Purpose
Fetch movie details, ratings, cast, and trailers from OMDB/TMDB.

## When to Activate
Activate when the user asks to:
- movie info
- tell me about film
- rating for <movie>

## Core Workflows

GET `http://www.omdbapi.com/?t=<title>&apikey=<KEY>`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
