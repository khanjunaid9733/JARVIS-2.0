#!/usr/bin/env python3
"""
JARVIS 2.0 — Auto-Creative Skill Engine (scripts/skill_creator.py)

Autonomously synthesizes and commits new skill definitions on demand.

Usage:
    python scripts/skill_creator.py create --name "my-skill" --prompt "JARVIS should be able to ..."
    python scripts/skill_creator.py list
    python scripts/skill_creator.py search --query "video"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path
from typing import Any

ROOT       = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / ".agents" / "skills"


# ---------------------------------------------------------------------------
# Skill Registry — auto-discovered from .agents/skills/
# ---------------------------------------------------------------------------

def scan_all_skills() -> list[dict[str, Any]]:
    """Scan all installed skills and return their metadata."""
    skills = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir():
            continue
        skill_file = d / "SKILL.md"
        if not skill_file.exists():
            continue
        text = skill_file.read_text(encoding="utf-8")
        name = d.name
        description = ""
        triggers: list[str] = []
        for line in text.splitlines():
            if line.startswith("description:"):
                description = line.split("description:", 1)[1].strip()
            if line.strip().startswith("- ") and "activate" not in description.lower():
                triggers.append(line.strip()[2:])
        skills.append({"id": name, "description": description, "triggers": triggers[:5]})
    return skills


def search_skills(query: str) -> list[dict[str, Any]]:
    """Fuzzy keyword search over installed skills."""
    q = query.lower()
    return [
        s for s in scan_all_skills()
        if q in s["id"].lower()
        or q in s["description"].lower()
        or any(q in t.lower() for t in s["triggers"])
    ]


# ---------------------------------------------------------------------------
# Skill Creator — generates a new SKILL.md from a freeform prompt
# ---------------------------------------------------------------------------

SKILL_TEMPLATE = """\
---
name: {name}
description: {description}
---

# {title} Skill

## Purpose
{description}

## When to Activate
Activate when the user asks to:
{triggers}

## Core Workflows

{workflows}

## Prerequisites
{prerequisites}

## Best Practices & Safety Invariants
- Verify all preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream `skill.{name}`.
- Fail-closed with descriptive error messages.
- Never log raw secrets or PII into durable payloads.
- Adhere to the JARVIS External Capability Substitution Seam.
"""


def _kebab(name: str) -> str:
    """Normalize a name to kebab-case."""
    return name.lower().replace(" ", "-").replace("_", "-")


def _llm_create_skill(name: str, prompt: str) -> dict[str, str]:
    """
    Use the JARVIS ModelGateway to synthesize skill fields from a freeform prompt.
    Falls back to a structured template if no model backend is configured.
    """
    sys.path.insert(0, str(ROOT / "src"))
    api_key  = os.environ.get("JARVIS_MODEL_API_KEY")
    base_url = os.environ.get("JARVIS_MODEL_BASE_URL")

    if api_key and base_url:
        try:
            from jarvis.providers.openai_compatible import OpenAICompatibleAdapter
            import asyncio

            model = os.environ.get("JARVIS_MODEL_NAME", "openai/gpt-oss-120b")
            adapter = OpenAICompatibleAdapter(model=model)
            full_prompt = textwrap.dedent(f"""
                You are JARVIS 2.0's skill synthesis engine.
                Create a skill specification from the following description:

                SKILL NAME: {name}
                USER REQUEST: {prompt}

                Return ONLY a JSON object with these exact keys:
                - "description": one-sentence skill description (<120 chars)
                - "title": human-readable title (2-5 words)
                - "triggers": list of 5-8 trigger phrases the user might say
                - "workflows": markdown-formatted step-by-step instructions (use code blocks where appropriate)
                - "prerequisites": list of required libraries, API keys, or tools

                JSON ONLY. No extra text.
            """).strip()

            # Try calling the adapter via its contract method
            call_fn = getattr(adapter, "generate", None) or getattr(adapter, "complete", None) or getattr(adapter, "call", None)
            if call_fn is None:
                raise AttributeError("No compatible generate/complete/call method on adapter")
            result = asyncio.run(call_fn(full_prompt)) if asyncio.iscoroutinefunction(call_fn) else call_fn(full_prompt)
            text = result.get("content", "") if isinstance(result, dict) else str(result)
            # Extract JSON from response
            start = text.find("{")
            end   = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception as exc:
            print(f"[skill_creator] Model gateway unavailable ({exc}), using template fallback.", file=sys.stderr)

    # Deterministic fallback
    return {
        "description": f"Enables JARVIS to {prompt.lower()[:100]}.",
        "title": " ".join(w.capitalize() for w in name.split("-")[:4]),
        "triggers": [
            f"perform {name.replace('-', ' ')}",
            f"help me {prompt.split()[0].lower()} something",
            f"automate {name.replace('-', ' ')}",
            f"{name.replace('-', ' ')} task",
            f"start {name.replace('-', ' ')}",
        ],
        "workflows": textwrap.dedent(f"""
            ### 1. {prompt[:60]}
            TODO: Implement the core workflow for this skill.

            ```python
            # Add implementation here
            # Connect to required services via JARVIS ProviderAdapter protocol
            ```

            ### 2. Error Handling
            - Validate all inputs before execution.
            - Catch and log all exceptions with descriptive messages.
        """).strip(),
        "prerequisites": "None specified. Add required libraries and API keys here.",
    }


def create_skill(name: str, prompt: str, overwrite: bool = False) -> Path:
    """Synthesize and write a new skill definition."""
    skill_id  = _kebab(name)
    skill_dir = SKILLS_DIR / skill_id
    skill_file = skill_dir / "SKILL.md"

    if skill_file.exists() and not overwrite:
        print(f"⚠️  Skill '{skill_id}' already exists at {skill_file}.")
        print("    Use --overwrite to replace it.")
        return skill_file

    print(f"🧠 Synthesizing skill: {skill_id} ...")
    fields = _llm_create_skill(skill_id, prompt)

    skill_dir.mkdir(parents=True, exist_ok=True)
    trigger_list = "\n".join(f"- {t}" for t in fields.get("triggers", []))
    content = SKILL_TEMPLATE.format(
        name        = skill_id,
        title       = fields.get("title", skill_id),
        description = fields.get("description", prompt),
        triggers    = trigger_list,
        workflows   = fields.get("workflows", "TODO: Implement workflows."),
        prerequisites = fields.get("prerequisites", "None."),
    )
    skill_file.write_text(content, encoding="utf-8")
    print(f"✅ Created skill: {skill_file}")
    return skill_file


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_create(args: argparse.Namespace) -> None:
    path = create_skill(args.name, args.prompt, overwrite=getattr(args, "overwrite", False))
    print(f"\n📁 Skill saved to: {path}")

    # Commit to JARVIS memory
    try:
        sys.path.insert(0, str(ROOT / "src"))
        import subprocess
        jarvis = ROOT / ".venv" / "Scripts" / "jarvis.exe"
        if jarvis.exists():
            result = subprocess.run(
                [str(jarvis), "say",
                 f"remember: [New Skill Acquired] {args.name}: {args.prompt[:100]}"],
                capture_output=True, text=True, cwd=ROOT
            )
            if "committed" in result.stdout:
                print("💾 Skill committed to JARVIS durable memory.")
    except Exception:
        pass


def cmd_list(args: argparse.Namespace) -> None:
    skills = scan_all_skills()
    print(f"\n📚 JARVIS Skill Library — {len(skills)} skills installed\n")
    print(f"{'ID':<45} {'DESCRIPTION'}")
    print("-" * 100)
    for s in skills:
        desc = s["description"][:55] + "..." if len(s["description"]) > 55 else s["description"]
        print(f"{s['id']:<45} {desc}")


def cmd_search(args: argparse.Namespace) -> None:
    results = search_skills(args.query)
    print(f"\n🔍 Search: '{args.query}' — {len(results)} matches\n")
    for s in results:
        print(f"  📌 {s['id']}")
        print(f"     {s['description']}")
        if s["triggers"]:
            print(f"     Triggers: {', '.join(s['triggers'][:3])}")
        print()


def cmd_domains(args: argparse.Namespace) -> None:
    """Show skill count by domain prefix."""
    skills = scan_all_skills()
    domains: dict[str, int] = {}
    for s in skills:
        prefix = s["id"].split("-")[0]
        domains[prefix] = domains.get(prefix, 0) + 1
    print(f"\n🌐 Domains ({len(domains)} total)\n")
    for d, count in sorted(domains.items(), key=lambda x: -x[1]):
        print(f"  {d:<20} {count:>4} skills")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="skill_creator",
        description="JARVIS 2.0 — Auto-Creative Skill Engine"
    )
    sub = parser.add_subparsers(dest="command")

    p_create = sub.add_parser("create", help="Synthesize a new skill")
    p_create.add_argument("--name",      required=True, help="Skill name in kebab-case (e.g. smart-home-control)")
    p_create.add_argument("--prompt",    required=True, help="Natural language description of what JARVIS should be able to do")
    p_create.add_argument("--overwrite", action="store_true", help="Overwrite existing skill if present")
    p_create.set_defaults(func=cmd_create)

    p_list = sub.add_parser("list", help="List all installed skills")
    p_list.set_defaults(func=cmd_list)

    p_search = sub.add_parser("search", help="Search installed skills")
    p_search.add_argument("--query", required=True)
    p_search.set_defaults(func=cmd_search)

    p_domains = sub.add_parser("domains", help="Show skill distribution by domain")
    p_domains.set_defaults(func=cmd_domains)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
