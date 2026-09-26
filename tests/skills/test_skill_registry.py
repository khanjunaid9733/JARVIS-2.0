from __future__ import annotations

from pathlib import Path
import pytest

from jarvis.skills.manifest import parse_skill_markdown
from jarvis.skills.registry import SkillRegistry, get_default_registry


def _make_skill(skill_id: str, desc: str, triggers: list[str]) -> object:
    body = f"""---
name: {skill_id}
description: {desc}
---

# {skill_id.title()} Skill

## Purpose
{desc}

## When to Activate
""" + "\n".join(f"- {t}" for t in triggers) + """

## Core Workflows
```bash
echo "doing work"
```
"""
    return parse_skill_markdown(body)


def test_registry_registration_and_lookup():
    reg = SkillRegistry()
    s1 = _make_skill("media-audio-convert", "Convert audio files between MP3 and WAV", ["convert audio", "to mp3"])
    s2 = _make_skill("cloud-aws-s3-upload", "Upload files to AWS S3 bucket", ["s3 upload", "aws upload"])
    s3 = _make_skill("cloud-aws-s3-list", "List files in AWS S3 bucket", ["s3 list", "list bucket"])

    reg.register(s1)
    reg.register(s2)
    reg.register(s3)

    assert reg.count() == 3
    assert reg.get("media-audio-convert") is s1
    assert reg.get("non-existent") is None
    assert reg.list_domains() == ["cloud", "media"]
    assert len(reg.get_by_domain("cloud")) == 2


def test_registry_natural_language_search():
    reg = SkillRegistry()
    s1 = _make_skill("media-audio-convert", "Convert audio files between MP3 and WAV", ["convert audio", "to mp3"])
    s2 = _make_skill("cloud-aws-s3-upload", "Upload files to AWS S3 bucket", ["s3 upload", "aws upload"])
    s3 = _make_skill("db-sqlite-query", "Execute SQL queries against local SQLite database", ["run sql query", "sqlite select"])

    reg.register(s1)
    reg.register(s2)
    reg.register(s3)

    # Search for audio conversion
    matches = reg.find("convert my audio file to mp3")
    assert len(matches) > 0
    assert matches[0].skill.id == "media-audio-convert"

    # Search for database query
    db_matches = reg.find("run a sql select query")
    assert len(db_matches) > 0
    assert db_matches[0].skill.id == "db-sqlite-query"

    # Search with domain filter
    cloud_matches = reg.find("upload", domain="cloud")
    assert len(cloud_matches) == 1
    assert cloud_matches[0].skill.id == "cloud-aws-s3-upload"


def test_default_registry_loads_repository_skills():
    reg = get_default_registry()
    # Check that repo's skills loaded cleanly
    assert reg.count() >= 50, f"Expected at least 50 skills loaded, got {reg.count()}"
    assert "media" in reg.list_domains()
    # Verify search on real skills
    res = reg.find("convert audio")
    assert any(m.skill.domain == "media" for m in res)


def test_registry_re_registration_is_idempotent():
    reg = SkillRegistry()
    skill = _make_skill("media-audio-convert", "Convert audio files between MP3 and WAV", ["convert audio", "to mp3"])

    reg.register(skill)
    initial_tokens = reg._inverted_index["audio"]["media-audio-convert"]
    initial_total_doc_len = reg._total_doc_len

    # Re-register identical skill
    reg.register(skill)

    # Invariant: weights and document lengths must remain identical
    assert reg._inverted_index["audio"]["media-audio-convert"] == initial_tokens
    assert reg._total_doc_len == initial_total_doc_len
    assert reg.count() == 1


def test_registry_unregister_purges_postings():
    reg = SkillRegistry()
    skill = _make_skill("media-audio-convert", "Convert audio files between MP3 and WAV", ["convert audio", "to mp3"])
    reg.register(skill)

    assert reg.contains("media-audio-convert")
    assert "audio" in reg._inverted_index

    # Unregister
    assert reg.unregister("media-audio-convert") is True
    assert not reg.contains("media-audio-convert")
    assert reg.get("media-audio-convert") is None
    assert "media-audio-convert" not in reg._inverted_index.get("audio", {})
    assert reg.count() == 0
    assert reg._total_doc_len == 0

