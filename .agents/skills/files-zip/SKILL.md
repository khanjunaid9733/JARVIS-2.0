---
name: files-zip
description: Create zip, tar.gz, or 7z archives from files or folders.
---

# Zip / Archive Skill

## Purpose
Create zip, tar.gz, or 7z archives from files or folders.

## When to Activate
Activate when the user asks to:
- zip <folder>
- compress <file>
- archive <directory>

## Core Workflows

```python
shutil.make_archive(output, 'zip', folder)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
