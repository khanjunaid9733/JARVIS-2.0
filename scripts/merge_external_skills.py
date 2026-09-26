from __future__ import annotations

"""Merge external skills from Composio and Claude Code Templates into JARVIS 2.0.

Scans:
- tmp_repos/awesome-claude-skills/
- tmp_repos/claude-code-templates/cli-tool/components/skills/

Normalizes, validates, and commits missing skills into .agents/skills/.
"""

import os
import re
import shutil
import sys
from pathlib import Path


def clean_skill_id(name: str) -> str:
    """Normalize skill name into kebab-case identifier."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\-]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name


def extract_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract YAML frontmatter if present."""
    frontmatter = {}
    body = text
    pattern = r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        raw_yaml = match.group(1)
        body = match.group(2)
        for line in raw_yaml.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                frontmatter[k.strip()] = v.strip().strip("'\"")
    return frontmatter, body


def format_skill_md(skill_id: str, description: str, body: str) -> str:
    """Ensure standard frontmatter and structure."""
    frontmatter, clean_body = extract_frontmatter(body)
    desc = frontmatter.get("description") or description or f"Automation skill for {skill_id}"
    desc = desc.replace("\n", " ").strip()
    
    # If body doesn't start with a heading, add one
    if not clean_body.strip().startswith("#"):
        clean_body = f"# {skill_id.replace('-', ' ').title()}\n\n" + clean_body

    return f"""---
name: {skill_id}
description: {desc}
---

{clean_body.strip()}
"""


def main() -> int:
    target_skills_dir = Path(".agents/skills").resolve()
    target_skills_dir.mkdir(parents=True, exist_ok=True)

    existing_skill_ids = {p.name for p in target_skills_dir.iterdir() if p.is_dir()}
    print(f"Current skills in .agents/skills/: {len(existing_skill_ids)}")

    newly_merged = 0
    skipped_existing = 0

    sources = [
        # Composio & awesome claude skills
        Path("tmp_repos/awesome-claude-skills"),
        # Claude code templates
        Path("tmp_repos/claude-code-templates/cli-tool/components/skills"),
    ]

    for source_root in sources:
        if not source_root.exists():
            print(f"Warning: source root {source_root} does not exist, skipping.")
            continue

        print(f"\nScanning: {source_root}...")
        for skill_file in source_root.glob("**/SKILL.md"):
            try:
                content = skill_file.read_text(encoding="utf-8", errors="replace")
                frontmatter, body = extract_frontmatter(content)
                
                # Determine ID
                raw_name = frontmatter.get("name") or skill_file.parent.name
                skill_id = clean_skill_id(raw_name)
                if not skill_id or skill_id in ("skills", "components"):
                    skill_id = clean_skill_id(skill_file.parent.name)

                # Avoid collision or duplicate
                if skill_id in existing_skill_ids:
                    skipped_existing += 1
                    continue

                dest_dir = target_skills_dir / skill_id
                dest_dir.mkdir(parents=True, exist_ok=True)

                desc = frontmatter.get("description", "")
                formatted_content = format_skill_md(skill_id, desc, content)
                (dest_dir / "SKILL.md").write_text(formatted_content, encoding="utf-8")

                # Copy any sibling resources/scripts/templates if present
                for sibling in skill_file.parent.iterdir():
                    if sibling.name == "SKILL.md":
                        continue
                    dest_sibling = dest_dir / sibling.name
                    if sibling.is_dir() and not dest_sibling.exists():
                        try:
                            shutil.copytree(sibling, dest_sibling)
                        except Exception:
                            pass
                    elif sibling.is_file() and not dest_sibling.exists():
                        try:
                            shutil.copy2(sibling, dest_sibling)
                        except Exception:
                            pass

                existing_skill_ids.add(skill_id)
                newly_merged += 1
            except Exception as e:
                # Silently skip malformed individual skills
                continue

    print(f"\n==========================================")
    print(f"MERGE COMPLETE:")
    print(f"  New skills merged:     {newly_merged}")
    print(f"  Skipped (existing):    {skipped_existing}")
    print(f"  Total JARVIS skills:   {len(existing_skill_ids)}")
    print(f"==========================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
