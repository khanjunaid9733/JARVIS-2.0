---
name: file-and-data-management
description: Manages files, folders, and data on the local filesystem. Supports create, read, update, delete, move, copy, rename, search, zip/unzip, and content transformation. Also handles CSV, JSON, and text data parsing.
---

# File & Data Management Skill

## Purpose
Enables JARVIS to interact with the local filesystem and data files — reading configs, processing CSVs, organizing directories, compressing archives, and transforming data formats.

## When to Activate
- "Read the file at <path>"
- "Write/save <content> to <path>"
- "Search for files matching <pattern>"
- "Zip/compress <folder>"
- "Parse the CSV at <path>"
- "List all files in <directory>"
- "Move/copy <file> to <destination>"
- "Create a new folder at <path>"
- "Find all .py files modified in the last 7 days"

## Core Workflows

### 1. Read a File
```python
from pathlib import Path

def read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")
```

### 2. Write / Append a File (Atomic Write)
```python
import tempfile, os

def write_file_atomic(path: str, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=p.parent, delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp = f.name
    os.replace(tmp, str(p))  # atomic rename
```

### 3. Search Files by Pattern
```python
import glob

def search_files(directory: str, pattern: str) -> list[str]:
    return glob.glob(f"{directory}/**/{pattern}", recursive=True)
```

### 4. Zip / Compress a Folder
```python
import shutil

def zip_folder(folder: str, output: str) -> str:
    return shutil.make_archive(output, "zip", folder)
```

### 5. Parse CSV
```python
import csv

def read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
```

### 6. Parse JSON
```python
import json

def read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
```

### 7. Find Recently Modified Files
```python
import os, time

def recently_modified(directory: str, days: int = 7) -> list[str]:
    cutoff = time.time() - days * 86400
    results = []
    for root, _, files in os.walk(directory):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.getmtime(fp) > cutoff:
                results.append(fp)
    return results
```

## Best Practices & Safety Invariants
- **Path Jailing**: Always resolve paths relative to a declared workspace root. Never write outside `JARVIS_HOME` or creator-authorized directories without explicit permission.
- **Atomic Writes**: Always use temp-file + os.replace to prevent partial writes.
- **PII Check**: Before writing any content to the event log, strip full file contents — log only path and byte-count for audit.
