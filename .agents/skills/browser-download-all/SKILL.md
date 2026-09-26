---
name: browser-download-all
description: Download all files of a specific type from a website.
---

# Bulk File Downloader Skill

## Purpose
Download all files of a specific type from a website.

## When to Activate
Activate when the user asks to:
- download all PDFs
- bulk download
- download all files from

## Core Workflows

Crawl page links, filter by extension, download each to local directory.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
