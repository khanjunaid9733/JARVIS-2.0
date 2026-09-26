---
name: files-unzip
description: Extract zip, tar.gz, 7z, or rar archives.
---

# Extract Archive Skill

## Purpose
Extract zip, tar.gz, 7z, or rar archives.

## When to Activate
Activate when the user asks to:
- unzip <file>
- extract archive
- decompress <file>

## Core Workflows

```python
shutil.unpack_archive(path, extract_to)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
