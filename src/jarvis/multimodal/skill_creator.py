"""Dynamic Skill Creator for JARVIS.

Enables JARVIS to autonomously synthesize, format, and install new skills
directly into the user's Antigravity/Gemini skills directory on voice command.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


GLOBAL_SKILLS_DIR = Path(r"C:\Users\khanj\.gemini\config\skills")
WORKSPACE_SKILLS_DIR = Path(r"F:\JARVIS2.0\.agents\skills")


@dataclass(frozen=True)
class SkillCreationResult:
    """Outcome of creating an autonomous skill."""
    success: bool
    skill_name: str
    target_path: str
    description: str
    message: str


def sanitize_skill_name(raw_name: str) -> str:
    """Convert an arbitrary phrase into a valid kebab-case skill identifier."""
    # Strip common prefixes and phrases
    name = raw_name.lower().strip()
    name = re.sub(r"^(hey\s+)?(jarvis|assistant)\s*,?\s*", "", name)
    name = re.sub(r"^(please\s+|can\s+you\s+|could\s+you\s+)?", "", name)
    name = re.sub(r"^(create|build|make|add|write|generate)\s+(a\s+)?(new\s+)?skill\s+(for|to|called|named)?\s*", "", name)
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name).strip("-")
    if not name:
        return "custom-skill"
    # Ensure length bounds (up to 4 descriptive tokens)
    tokens = [t for t in name.split("-") if t]
    return "-".join(tokens[:4]) or "custom-skill"


def is_skill_creation_intent(user_text: str) -> bool:
    """Determine whether the user utterance requests building or adding a skill."""
    lower = user_text.lower().strip()
    patterns = [
        r"\b(create|build|make|add|generate|write)\b.*\b(skill|capability)\b",
        r"\b(new\s+skill)\b",
        r"\b(skill\s+for)\b",
        r"\bbuild\s+that\s+capability\b",
    ]
    return any(bool(re.search(p, lower)) for p in patterns)


def extract_skill_topic(user_prompt: str) -> str:
    """Extract clean domain/topic from an arbitrary user instruction."""
    name = user_prompt.strip()
    name = re.sub(r"^(hey\s+)?(jarvis|assistant)\s*,?\s*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^(please\s+|can\s+you\s+|could\s+you\s+)?", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^(create|build|make|add|write|generate)\s+(a\s+)?(new\s+)?skill\s+(for|to|called|named)?\s*", "", name, flags=re.IGNORECASE)
    name = name.strip()
    return name if name else "Custom Automation"


def generate_skill_content(skill_name: str, topic: str, instructions: str = "") -> str:
    """Generate canonical Antigravity/Gemini SKILL.md formatted content with YAML frontmatter."""
    clean_topic = extract_skill_topic(topic)
    if not clean_topic or clean_topic == "Custom Automation":
        clean_topic = skill_name.replace("-", " ").title()

    skill_desc = f"Comprehensive workflow and guidance for {clean_topic}."
    
    return f"""---
name: {skill_name}
description: {skill_desc}
---

# {clean_topic.title()} Skill

## Purpose
This skill provides structured workflows, automation procedures, and actionable
commands for {clean_topic}.

## When to Activate
Activate this skill whenever the user asks to:
- Perform actions related to {clean_topic}
- Automate, configure, or troubleshoot {clean_topic}
- Execute tasks within this domain

## Core Workflows
{instructions if instructions.strip() else f"1. Analyze the user's specific requirements for {clean_topic}.\\n2. Validate required environment prerequisites.\\n3. Execute the corresponding operations deterministically.\\n4. Verify outcome and report completion back to the user."}

## Best Practices
- Always verify preconditions before initiating actions.
- Provide clear, auditable status messages.
- Fail closed with actionable remediation upon encountering errors.
"""


class SkillCreator:
    """Autonomous skill authoring and installation engine."""

    def __init__(
        self,
        global_skills_dir: Path | str = GLOBAL_SKILLS_DIR,
        workspace_skills_dir: Path | str = WORKSPACE_SKILLS_DIR,
    ) -> None:
        self.global_skills_dir = Path(global_skills_dir)
        self.workspace_skills_dir = Path(workspace_skills_dir)

    def create_skill(
        self,
        user_prompt: str,
        llm_engine: Optional[Any] = None,
        custom_instructions: str = "",
    ) -> SkillCreationResult:
        """Parse user prompt, generate skill markdown, and persist to disk."""
        skill_name = sanitize_skill_name(user_prompt)

        # If LLM is available, generate richer instructions
        instructions = custom_instructions
        if not instructions and llm_engine is not None and getattr(llm_engine, "is_online", False):
            try:
                prompt_messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert agent skill architect. Output ONLY 3-5 concise, practical, "
                            "bulleted implementation steps/instructions for the requested skill. "
                            "Do not include YAML frontmatter or title headers."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Write procedural workflows and instructions for: {user_prompt}",
                    },
                ]
                resp = llm_engine.generate(prompt_messages)
                if resp and len(resp.strip()) > 10:
                    instructions = resp.strip()
            except Exception:
                pass

        content = generate_skill_content(skill_name, user_prompt, instructions)

        # Determine target locations (write to global skills directory by default)
        primary_dir = self.global_skills_dir / skill_name
        try:
            primary_dir.mkdir(parents=True, exist_ok=True)
            skill_file = primary_dir / "SKILL.md"
            skill_file.write_text(content, encoding="utf-8")

            # Also write to workspace directory if accessible
            try:
                ws_dir = self.workspace_skills_dir / skill_name
                ws_dir.mkdir(parents=True, exist_ok=True)
                (ws_dir / "SKILL.md").write_text(content, encoding="utf-8")
            except Exception:
                pass

            msg = (
                f"Right away, sir. I have synthesized and installed the new skill '{skill_name}'. "
                "It is now active in your skill library and ready for use."
            )
            return SkillCreationResult(
                success=True,
                skill_name=skill_name,
                target_path=str(skill_file),
                description=f"Skill for {user_prompt}",
                message=msg,
            )
        except Exception as exc:
            return SkillCreationResult(
                success=False,
                skill_name=skill_name,
                target_path="",
                description="",
                message=f"I encountered an error creating the skill: {exc}",
            )
