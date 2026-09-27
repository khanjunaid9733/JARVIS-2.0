from __future__ import annotations

import json
import tempfile
from pathlib import Path
import pytest

from jarvis.skills.manifest import (
    SkillManifest,
    SkillParameter,
    SkillPrerequisites,
    SkillWorkflowStep,
    load_skill_file,
    load_skills_directory,
    parse_skill_markdown,
)

SAMPLE_MARKDOWN = """---
name: media-audio-convert
description: Convert audio files between MP3, WAV, FLAC, AAC formats.
---

# Audio Converter Skill

## Purpose
Convert audio files between MP3, WAV, FLAC, AAC formats.

## When to Activate
Activate when the user asks to:
- convert audio
- convert to MP3
- audio format change

## Core Workflows

```bash
ffmpeg -i input.wav -q:a 0 output.mp3
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Fail-closed with descriptive error messages on any failure.
"""


def test_parse_skill_markdown_basic():
    manifest = parse_skill_markdown(SAMPLE_MARKDOWN)
    assert manifest.id == "media-audio-convert"
    assert manifest.domain == "media"
    assert manifest.title == "Audio Converter Skill"
    assert "Convert audio files" in manifest.description
    assert len(manifest.triggers) == 3
    assert "convert to MP3" in manifest.triggers
    assert len(manifest.workflow_steps) == 1
    assert manifest.workflow_steps[0].language == "bash"
    assert "ffmpeg" in manifest.workflow_steps[0].code
    assert manifest.is_runnable is True
    assert "ffmpeg" in manifest.prerequisites.required_binaries


def test_parse_skill_with_python_code():
    doc = """---
name: ds-clustering
description: Cluster data points using K-Means or DBSCAN.
---

# Clustering Analysis

## Purpose
Perform data clustering.

## When to Activate
- cluster data
- run kmeans

## Core Workflows

```python
import sklearn
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=3).fit(data)
```
"""
    manifest = parse_skill_markdown(doc)
    assert manifest.id == "ds-clustering"
    assert manifest.domain == "ds"
    assert manifest.is_runnable is True
    assert "sklearn" in manifest.prerequisites.required_python_modules


def test_load_skill_file_and_directory(tmp_path):
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(SAMPLE_MARKDOWN, encoding="utf-8")

    loaded = load_skill_file(skill_file)
    assert loaded.id == "media-audio-convert"

    dir_skills = load_skills_directory(tmp_path / "skills")
    assert "media-audio-convert" in dir_skills
    assert dir_skills["media-audio-convert"].title == "Audio Converter Skill"


def test_directory_cache_is_written_as_valid_json_and_reloads(tmp_path):
    """Regression: the cache writer once referenced an unimported `json`,
    so every write was swallowed and the file stayed zero bytes - forcing a
    full re-parse of the library on every registry build."""
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SAMPLE_MARKDOWN, encoding="utf-8")

    first = load_skills_directory(tmp_path / "skills")
    cache_file = tmp_path / "skills" / ".skills_cache.json"
    assert cache_file.is_file()
    assert cache_file.stat().st_size > 0
    cached = json.loads(cache_file.read_text(encoding="utf-8"))
    assert "media-audio-convert" in cached

    # A second load must hydrate from the cache and produce an equal manifest.
    second = load_skills_directory(tmp_path / "skills")
    assert set(second) == set(first)
    assert second["media-audio-convert"].title == first["media-audio-convert"].title

    # The atomic writer must not leave temporary files behind.
    assert not list((tmp_path / "skills").glob(".skills_cache.*.tmp"))


def test_directory_cache_recovers_from_a_corrupt_cache_file(tmp_path):
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SAMPLE_MARKDOWN, encoding="utf-8")

    cache_file = tmp_path / "skills" / ".skills_cache.json"
    cache_file.write_text("", encoding="utf-8")  # the exact broken state seen on disk

    loaded = load_skills_directory(tmp_path / "skills")
    assert "media-audio-convert" in loaded
    assert cache_file.stat().st_size > 0


def test_directory_cache_is_invalidated_when_the_library_changes(tmp_path):
    """Regression: the cache was served blindly, so editing, adding or removing a
    SKILL.md had no effect until the cache file was deleted by hand - a caller
    (e.g. a mission) would execute a stale skill definition with no warning."""
    skills_root = tmp_path / "skills"
    skill_dir = skills_root / "test-skill"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
    assert "media-audio-convert" in load_skills_directory(skills_root)

    # 1. an edit is picked up (different description, different size)
    skill_file.write_text(
        SAMPLE_MARKDOWN.replace("FLAC, AAC formats", "FLAC, AAC, and OGG formats"),
        encoding="utf-8",
    )
    edited = load_skills_directory(skills_root)
    assert "OGG" in edited["media-audio-convert"].description

    # 2. an added skill appears
    added_dir = skills_root / "second-skill"
    added_dir.mkdir()
    (added_dir / "SKILL.md").write_text(
        SAMPLE_MARKDOWN.replace("media-audio-convert", "second-skill"), encoding="utf-8"
    )
    assert "second-skill" in load_skills_directory(skills_root)

    # 3. a removed skill disappears
    (added_dir / "SKILL.md").unlink()
    assert "second-skill" not in load_skills_directory(skills_root)

    # the cache stays a cache: re-reading it is still valid JSON with metadata
    cached = json.loads((skills_root / ".skills_cache.json").read_text(encoding="utf-8"))
    assert cached["__cache_meta__"]["files"]


def test_load_skills_directory_deterministic_duplicate_collision_handling(tmp_path, caplog):
    import logging
    skills_root = tmp_path / "skills"
    dir_a = skills_root / "01_first"
    dir_b = skills_root / "02_second"
    dir_a.mkdir(parents=True)
    dir_b.mkdir(parents=True)

    markdown_first = """---
name: duplicate-test-skill
description: First definition
---
# First Definition
"""
    markdown_second = """---
name: duplicate-test-skill
description: Second definition
---
# Second Definition
"""
    (dir_a / "SKILL.md").write_text(markdown_first, encoding="utf-8")
    (dir_b / "SKILL.md").write_text(markdown_second, encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        loaded = load_skills_directory(skills_root, use_cache=False)

    assert len(loaded) == 1
    assert "duplicate-test-skill" in loaded
    # Invariant: deterministic sorting ensures first parsed definition is retained
    assert loaded["duplicate-test-skill"].description == "First definition"
    assert any("Duplicate skill ID" in r.message for r in caplog.records)

