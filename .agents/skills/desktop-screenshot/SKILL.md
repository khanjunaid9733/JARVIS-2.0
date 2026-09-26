---
name: desktop-screenshot
description: Capture the full screen, a window, or a region and save as PNG.
---

# Screenshot Skill

## Purpose
Capture the full screen, a window, or a region and save as PNG.

## When to Activate
Activate when the user asks to:
- take a screenshot
- capture screen
- screenshot

## Core Workflows

```powershell
Add-Type -AssemblyName System.Drawing; # CopyFromScreen -> .Save('path.png')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
