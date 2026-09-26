from __future__ import annotations

"""Skill Manifest and Parser for JARVIS 2.0.

Provides strongly typed Pydantic models for skill specifications, parsing
YAML frontmatter and markdown sections (Purpose, Triggers, Prerequisites,
Parameters, Workflows, Safety Invariants) from SKILL.md documents.
"""

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence
from pydantic import BaseModel, Field

logger = logging.getLogger("jarvis.skills.manifest")


class SkillParameter(BaseModel):
    """Specification of a skill parameter."""

    name: str
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""


class SkillPrerequisites(BaseModel):
    """Execution prerequisites declared by a skill."""

    required_binaries: list[str] = Field(default_factory=list)
    required_env_vars: list[str] = Field(default_factory=list)
    required_python_modules: list[str] = Field(default_factory=list)
    requires_network: bool = False


class SkillWorkflowStep(BaseModel):
    """A discrete workflow step or executable snippet."""

    step_index: int
    title: str = ""
    language: str = "bash"  # bash, powershell, python, http, text
    code: str = ""


class SkillManifest(BaseModel):
    """Strongly-typed representation of a JARVIS skill."""

    id: str
    name: str
    domain: str
    title: str = ""
    description: str = ""
    version: str = "1.0.0"
    triggers: list[str] = Field(default_factory=list)
    prerequisites: SkillPrerequisites = Field(default_factory=SkillPrerequisites)
    parameters: list[SkillParameter] = Field(default_factory=list)
    workflow_steps: list[SkillWorkflowStep] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    source_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_runnable(self) -> bool:
        """True if the skill contains executable workflow steps."""
        return any(
            s.language in ("bash", "powershell", "python", "http") and bool(s.code.strip())
            for s in self.workflow_steps
        )


def _extract_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Extract YAML frontmatter between --- markers if present."""
    frontmatter: dict[str, str] = {}
    body = content

    pattern = r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        raw_yaml = match.group(1)
        body = match.group(2)
        for line in raw_yaml.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                frontmatter[key.strip()] = val.strip().strip("'\"")

    return frontmatter, body


def _extract_domain(skill_id: str) -> str:
    """Infer domain from skill_id prefix (e.g., 'media-audio-convert' -> 'media')."""
    if "-" in skill_id:
        return skill_id.split("-", 1)[0]
    return "general"


def _extract_section(body: str, heading_pattern: str) -> str:
    """Extract text under a specific markdown heading until the next heading of same or higher level."""
    pattern = rf"^##\s+(?:{heading_pattern})\s*$(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, body, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if match and match.group(1) is not None:
        return match.group(1).strip()
    return ""


def _extract_bullets(section_text: str) -> list[str]:
    """Extract bullet points (- or *) from markdown text."""
    bullets: list[str] = []
    for line in section_text.splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ")):
            item = line[2:].strip()
            if item:
                bullets.append(item)
    return bullets


def _extract_code_blocks(body: str) -> list[SkillWorkflowStep]:
    """Extract code blocks with language from markdown body."""
    steps: list[SkillWorkflowStep] = []
    pattern = r"```([a-zA-Z0-9_\-]+)?\r?\n(.*?)\r?\n```"
    matches = re.finditer(pattern, body, re.DOTALL)
    for idx, match in enumerate(matches, 1):
        lang = (match.group(1) or "bash").lower()
        code = match.group(2).strip()
        steps.append(
            SkillWorkflowStep(
                step_index=idx,
                title=f"Step {idx}",
                language=lang,
                code=code,
            )
        )
    return steps


def _infer_prerequisites(skill_id: str, body: str, workflow_steps: Sequence[SkillWorkflowStep]) -> SkillPrerequisites:
    """Infer common binaries, env vars, and packages from skill text and code."""
    binaries: set[str] = set()
    env_vars: set[str] = set()
    modules: set[str] = set()
    requires_network = False

    combined = body + "\n" + "\n".join(s.code for s in workflow_steps)

    # Detect known CLI binaries
    known_binaries = (
        "ffmpeg", "git", "docker", "curl", "tar", "zip", "unzip", "ssh", "sftp",
        "playwright", "npx", "node", "npm", "uv", "python", "powershell",
        "terraform", "sqlite3", "psql", "mysql", "redis-cli", "mongosh",
    )
    for b in known_binaries:
        if re.search(rf"\b{b}\b", combined):
            binaries.add(b)

    # Detect API keys / env vars
    env_pattern = r"\b([A-Z][A-Z0-9_]{3,}_(?:KEY|TOKEN|SECRET|ID|URL|PASSWORD))\b"
    for m in re.finditer(env_pattern, combined):
        env_vars.add(m.group(1))

    # Detect python imports in python code blocks
    for s in workflow_steps:
        if s.language == "python":
            for imp in re.finditer(r"^(?:import|from)\s+([a-zA-Z0-9_]+)", s.code, re.MULTILINE):
                mod = imp.group(1)
                if mod not in ("os", "sys", "json", "math", "re", "pathlib", "typing", "dataclasses", "asyncio", "urllib"):
                    modules.add(mod)

    # Network detection
    if any(k in combined.lower() for k in ("http://", "https://", "api", "curl", "urllib", "request", "download", "fetch", "webhook")):
        requires_network = True

    return SkillPrerequisites(
        required_binaries=sorted(binaries),
        required_env_vars=sorted(env_vars),
        required_python_modules=sorted(modules),
        requires_network=requires_network,
    )


def parse_skill_markdown(content: str, source_path: Path | str | None = None) -> SkillManifest:
    """Parse a SKILL.md file into a strongly-typed SkillManifest."""
    frontmatter, body = _extract_frontmatter(content)

    # ID and Name
    skill_id = frontmatter.get("name")
    if not skill_id and source_path:
        skill_id = Path(source_path).parent.name
    skill_id = skill_id or "unnamed-skill"

    name = frontmatter.get("name") or skill_id
    domain = _extract_domain(skill_id)
    description = frontmatter.get("description", "")

    # Extract Title from first # heading
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else name

    # If description missing from frontmatter, check ## Purpose
    if not description:
        description = _extract_section(body, "Purpose")
        if not description:
            description = title

    # Triggers from ## When to Activate
    activate_section = _extract_section(body, "When to Activate")
    triggers = _extract_bullets(activate_section)
    if not triggers and activate_section:
        triggers = [t.strip() for t in activate_section.splitlines() if t.strip()]

    # Workflow steps (code blocks)
    workflow_steps = _extract_code_blocks(body)

    # Safety invariants from ## Best Practices & Safety Invariants
    safety_section = _extract_section(body, r"Best Practices.*|Safety.*")
    safety_invariants = _extract_bullets(safety_section)

    # Infer prerequisites
    prerequisites = _infer_prerequisites(skill_id, body, workflow_steps)

    return SkillManifest(
        id=skill_id,
        name=name,
        domain=domain,
        title=title,
        description=description,
        triggers=triggers,
        prerequisites=prerequisites,
        workflow_steps=workflow_steps,
        safety_invariants=safety_invariants,
        source_path=str(source_path) if source_path else None,
        metadata={"raw_frontmatter": frontmatter},
    )


def load_skill_file(path: Path | str) -> SkillManifest:
    """Load and parse a single SKILL.md file from disk."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Skill file not found at: {p}")
    content = p.read_text(encoding="utf-8")
    return parse_skill_markdown(content, source_path=p)


def load_skills_directory(
    directory: Path | str,
    use_cache: bool = True,
) -> dict[str, SkillManifest]:
    """Recursively search for and load all SKILL.md files in a directory with optional caching."""
    root = Path(directory)
    if not root.is_dir():
        return {}

    cache_file = root / ".skills_cache.json"
    if use_cache and cache_file.is_file():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data:
                res: dict[str, SkillManifest] = {}
                for k, v in data.items():
                    prereqs = (
                        SkillPrerequisites.model_construct(**v.get("prerequisites", {}))
                        if isinstance(v.get("prerequisites"), dict)
                        else SkillPrerequisites()
                    )
                    steps = [
                        SkillWorkflowStep.model_construct(**s)
                        for s in v.get("workflow_steps", [])
                        if isinstance(s, dict)
                    ]
                    params = [
                        SkillParameter.model_construct(**p)
                        for p in v.get("parameters", [])
                        if isinstance(p, dict)
                    ]
                    clean_v = {**v}
                    clean_v["prerequisites"] = prereqs
                    clean_v["workflow_steps"] = steps
                    clean_v["parameters"] = params
                    res[k] = SkillManifest.model_construct(**clean_v)
                return res
        except Exception:
            pass

    skills: dict[str, SkillManifest] = {}
    for skill_file in sorted(root.glob("**/SKILL.md")):
        try:
            manifest = load_skill_file(skill_file)
            if manifest.id in skills:
                logger.warning(
                    "Duplicate skill ID %r detected at %s; retaining existing version from %s",
                    manifest.id,
                    skill_file,
                    skills[manifest.id].source_path,
                )
                continue
            skills[manifest.id] = manifest
        except Exception:
            # Skip invalid or unparseable files without crashing
            continue

    if use_cache and skills:
        _write_cache_atomically(cache_file, skills)

    return skills


def _write_cache_atomically(cache_file: Path, skills: Mapping[str, SkillManifest]) -> None:
    """Write the skill cache atomically so an interrupted write cannot leave a
    truncated file behind (a zero-byte cache is otherwise indistinguishable
    from a valid one on the next read)."""
    try:
        payload = json.dumps({k: v.model_dump() for k, v in skills.items()})
    except Exception:
        return
    tmp_path: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(
            prefix=".skills_cache.", suffix=".tmp", dir=str(cache_file.parent)
        )
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, cache_file)
    except Exception:
        # Cache is a performance optimization only; never let it break loading.
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
