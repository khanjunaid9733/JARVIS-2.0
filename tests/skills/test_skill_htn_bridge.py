from __future__ import annotations

import pytest

from jarvis.kernel.planner.htn import HTNPlanner
from jarvis.skills.htn_bridge import SkillHTNBridge, skill_to_operator
from jarvis.skills.manifest import parse_skill_markdown
from jarvis.skills.registry import SkillRegistry


def test_skill_to_operator_mapping():
    doc = """---
name: media-audio-convert
description: Convert audio files between formats.
---
# Audio Converter
## When to Activate
- convert audio
- to mp3
## Core Workflows
```bash
ffmpeg -i in.wav out.mp3
```
"""
    skill = parse_skill_markdown(doc)
    op = skill_to_operator(skill)

    assert op.id == "skill:media-audio-convert"
    assert op.contract_id == "jarvis.skill.media"
    assert op.action_type == "skill"
    assert "Convert audio" in op.summary


def test_htn_planner_decomposes_goal_via_skill_domain():
    reg = SkillRegistry()

    doc1 = """---
name: web-fetch-page
description: Fetch web page text.
---
# Web Fetch
## When to Activate
- fetch page
- download url
## Core Workflows
```python
print("fetched")
```
"""
    doc2 = """---
name: text-summarize
description: Summarize text document.
---
# Summarize
## When to Activate
- summarize text
- make summary
## Core Workflows
```python
print("summary")
```
"""
    s1 = parse_skill_markdown(doc1)
    s2 = parse_skill_markdown(doc2)
    s1.prerequisites.required_binaries.clear()
    s2.prerequisites.required_binaries.clear()

    reg.register(s1)
    reg.register(s2)

    bridge = SkillHTNBridge(reg)
    domain = bridge.build_domain()

    assert len(domain.operators) == 2
    assert any(op.id == "skill:web-fetch-page" for op in domain.operators)
    assert any(op.id == "skill:text-summarize" for op in domain.operators)

    planner = HTNPlanner(domain)

    # World state with bypass so health checks pass cleanly in unit test
    world_state = {"bypass_skill_health": True}

    # Plan compound task by trigger name!
    plan = planner.plan("fetch page", world_state)
    assert len(plan) == 1
    assert plan[0].id == "skill:web-fetch-page"

    plan2 = planner.plan("summarize text", world_state)
    assert len(plan2) == 1
    assert plan2[0].id == "skill:text-summarize"
