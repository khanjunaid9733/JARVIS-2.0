from __future__ import annotations

"""JARVIS Skill Runtime Foundation Package.

Provides a unified, deterministic runtime architecture for the 700+ skill
library, including typed parsing, in-memory inverted indexing, prerequisite
health checks, contained execution dispatch, HTN planner bridges, and
multi-skill pipeline composition.
"""

from .cognitive_agent import AgentTurnResult, CognitiveAgent, ToolExecutionRecord
from .composer import PipelineResult, PipelineStep, SkillPipelineComposer
from .context import SkillExecutionContext
from .dispatcher import SkillDispatcher, SkillExecutionResult
from .engine import SkillGoalResult, SkillRuntimeEngine
from .health import HealthStatus, SkillHealthChecker, SkillHealthReport
from .htn_bridge import SkillHTNBridge, skill_to_operator
from .manifest import (
    SkillManifest,
    SkillParameter,
    SkillPrerequisites,
    SkillWorkflowStep,
    load_skill_file,
    load_skills_directory,
    parse_skill_markdown,
)
from .registry import SkillMatch, SkillRegistry, get_default_registry
from .telemetry import (
    get_skill_metrics,
    record_skill_audit_failure,
    record_skill_dispatch,
)

__all__ = [
    "AgentTurnResult",
    "CognitiveAgent",
    "HealthStatus",
    "PipelineResult",
    "PipelineStep",
    "SkillDispatcher",
    "SkillExecutionContext",
    "SkillExecutionResult",
    "SkillGoalResult",
    "SkillHTNBridge",
    "SkillHealthChecker",
    "SkillHealthReport",
    "SkillManifest",
    "SkillMatch",
    "SkillParameter",
    "SkillPipelineComposer",
    "SkillPrerequisites",
    "SkillRegistry",
    "SkillRuntimeEngine",
    "SkillWorkflowStep",
    "get_default_registry",
    "get_skill_metrics",
    "record_skill_audit_failure",
    "load_skill_file",
    "load_skills_directory",
    "parse_skill_markdown",
    "record_skill_dispatch",
    "skill_to_operator",
]
