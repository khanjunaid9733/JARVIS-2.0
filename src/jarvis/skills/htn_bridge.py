from __future__ import annotations

"""Bridge between the Skill Library and the JARVIS HTN Planner (Milestone M5.1).

Enables Hierarchical Task Network planning over registered skills, translating
skills into PrimitiveOperators and compound DomainMethods for autonomous
mission decomposition and ManifestDAG compilation.
"""

from typing import Any, Callable, Mapping, Sequence

from jarvis.kernel.planner.types import (
    DomainMethod,
    HTNDomain,
    Precondition,
    PrimitiveOperator,
)

from .health import SkillHealthChecker
from .manifest import SkillManifest
from .registry import SkillRegistry


def skill_to_operator(skill: SkillManifest) -> PrimitiveOperator:
    """Translate a SkillManifest into an HTN PrimitiveOperator."""
    return PrimitiveOperator(
        id=f"skill:{skill.id}",
        summary=skill.description or skill.title or skill.name,
        action_type="skill",
        contract_id=f"jarvis.skill.{skill.domain}",
        version=skill.version,
        parameters={
            "skill_id": skill.id,
            "domain": skill.domain,
            "triggers": tuple(skill.triggers),
        },
    )


def make_skill_health_precondition(
    skill: SkillManifest,
    checker: SkillHealthChecker | None = None,
) -> Precondition:
    """Generate a Precondition that verifies the skill's operational readiness."""
    chk = checker or SkillHealthChecker()

    def _eval(state: Mapping[str, Any]) -> bool:
        # Check if caller explicitly bypassed or overrides in world_state
        if state.get("bypass_skill_health"):
            return True
        report = chk.evaluate(skill)
        return report.is_executable

    return Precondition(
        name=f"health_ok:{skill.id}",
        predicate=_eval,
        description=f"Verify prerequisites for skill {skill.id}",
    )


class SkillHTNBridge:
    """Builds and manages HTNDomains composed of registered JARVIS skills."""

    def __init__(
        self,
        registry: SkillRegistry,
        health_checker: SkillHealthChecker | None = None,
    ) -> None:
        self.registry = registry
        self.health_checker = health_checker or SkillHealthChecker()

    def build_domain(
        self,
        domain_name: str = "skills_runtime_domain",
        filter_healthy: bool = False,
    ) -> HTNDomain:
        """Construct an HTNDomain representing all or healthy skills."""
        operators: list[PrimitiveOperator] = []
        methods: list[DomainMethod] = []

        all_skills = self.registry.list_all()
        for skill in all_skills:
            if filter_healthy:
                report = self.health_checker.evaluate(skill)
                if not report.is_executable:
                    continue

            op = skill_to_operator(skill)
            operators.append(op)

            # Map triggers as alias tasks that decompose into this skill operator
            for trigger in skill.triggers:
                cleaned_trigger = trigger.lower().strip()
                if cleaned_trigger:
                    methods.append(
                        DomainMethod(
                            name=f"method_{skill.id}_{hash(cleaned_trigger) & 0xFFFF}",
                            task_name=cleaned_trigger,
                            preconditions=(make_skill_health_precondition(skill, self.health_checker),),
                            subtasks=(op.id,),
                        )
                    )

            # Also add domain-level compound task (e.g. task_name="media" -> skill)
            methods.append(
                DomainMethod(
                    name=f"method_domain_{skill.id}",
                    task_name=f"task:{skill.domain}",
                    preconditions=(make_skill_health_precondition(skill, self.health_checker),),
                    subtasks=(op.id,),
                )
            )

        return HTNDomain(
            name=domain_name,
            methods=tuple(methods),
            operators=tuple(operators),
        )
