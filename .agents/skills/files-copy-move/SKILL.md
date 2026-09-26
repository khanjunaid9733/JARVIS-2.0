---
name: files-copy-move
description: Copy or move files and directories between locations.
---

# Copy / Move Files Skill

## Purpose
Copy or move files and directories between locations.

## When to Activate
Activate when the user asks to:
- copy <file> to <dest>
- move <file>
- relocate folder

## Core Workflows

```python
shutil.copy2(src, dst)  # or shutil.move(src, dst)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
