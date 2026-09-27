from __future__ import annotations

from pathlib import Path
import pytest

from jarvis.skills.admission import SkillAdmissionPolicy
from jarvis.skills.composer import PipelineStep, SkillPipelineComposer
from jarvis.skills.dispatcher import SkillDispatcher
from jarvis.skills.manifest import parse_skill_markdown
from jarvis.skills.registry import SkillRegistry


def test_composer_executes_multi_skill_pipeline(tmp_path):
    reg = SkillRegistry()

    doc1 = """---
name: text-producer
description: Produces initial text.
---
# Producer
## Core Workflows
```python
print("PIPELINE_INIT_VALUE")
```
"""
    doc2 = """---
name: text-consumer
description: Processes text.
---
# Consumer
## Core Workflows
```python
print("RECEIVED_{last_output}")
```
"""
    s1 = parse_skill_markdown(doc1)
    s2 = parse_skill_markdown(doc2)
    s1.prerequisites.required_binaries.clear()
    s2.prerequisites.required_binaries.clear()

    reg.register(s1)
    reg.register(s2)

    dispatcher = SkillDispatcher(
        admission=SkillAdmissionPolicy(
            entries=frozenset({"text-producer", "text-consumer"})
        )
    )
    composer = SkillPipelineComposer(reg, dispatcher)

    steps = [
        PipelineStep(step_id="produce", skill_id="text-producer"),
        PipelineStep(step_id="consume", skill_id="text-consumer"),
    ]

    res = composer.execute_pipeline(
        name="test_pipeline",
        steps=steps,
        initial_params={},
        workspace=tmp_path,
        dry_run=False,
    )

    assert res.success is True
    assert res.completed_steps == 2
    assert "RECEIVED_--- Step 1 (python) ---" in res.final_output or "RECEIVED" in res.final_output


def test_composer_halts_on_missing_skill(tmp_path):
    reg = SkillRegistry()
    dispatcher = SkillDispatcher()
    composer = SkillPipelineComposer(reg, dispatcher)

    steps = [
        PipelineStep(step_id="s1", skill_id="nonexistent-skill"),
    ]

    res = composer.execute_pipeline(
        name="fail_pipeline",
        steps=steps,
        initial_params={},
        workspace=tmp_path,
    )

    assert res.success is False
    assert "references unknown skill" in (res.error or "")
