from __future__ import annotations

"""Automated Batch Verification & Health Assessment for JARVIS Skills.

Audits and evaluates all 2,400+ skills in .agents/skills/:
1. Frontmatter and Manifest parsing validity.
2. System requirement checks (binaries, env vars, python dependencies).
3. Skill categorization (Pure LLM/Prompt, Local Tool Executable, API/Cloud Dependent).
4. Dry-run execution verification through SkillDispatcher.
5. Export comprehensive verification report.
"""

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from jarvis.skills.manifest import SkillManifest, load_skill_file, load_skills_directory
from jarvis.skills.registry import SkillRegistry, get_default_registry
from jarvis.skills.health import SkillHealthChecker, HealthStatus
from jarvis.skills.dispatcher import SkillDispatcher
from jarvis.skills.context import SkillExecutionContext


def run_batch_verification(sample_limit: int | None = None) -> dict[str, Any]:
    print("=" * 70, flush=True)
    print("JARVIS SKILL SUITE VERIFICATION & HEALTH AUDIT", flush=True)
    print("=" * 70, flush=True)

    start_time = time.monotonic()
    registry = get_default_registry()
    total_skills = registry.count()
    print(f"[*] Registered Skills in Library: {total_skills}", flush=True)
    print(f"[*] Unique Domains Identified: {len(registry.list_domains())}", flush=True)

    checker = SkillHealthChecker()
    dispatcher = SkillDispatcher(health_checker=checker)
    base_context = SkillExecutionContext(workspace=PROJECT_ROOT, dry_run=True)

    # Metrics
    ready_count = 0
    missing_binaries_count = 0
    missing_env_count = 0
    missing_python_count = 0
    
    classification_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    
    missing_env_vars: Counter[str] = Counter()
    missing_binaries: Counter[str] = Counter()

    dry_run_successes = 0
    dry_run_failures = 0
    dry_run_samples: list[dict[str, Any]] = []

    all_skills = registry.list_all()
    if sample_limit:
        all_skills = all_skills[:sample_limit]

    print(f"[*] Auditing {len(all_skills)} skills...", flush=True)

    for i, skill in enumerate(all_skills):
        domain = skill.domain or "general"
        domain_counts[domain] += 1

        health = checker.evaluate(skill)
        
        # Categorize
        if health.status == HealthStatus.HEALTHY:
            ready_count += 1
            classification_counts["ready_to_execute"] += 1
        else:
            if health.missing_binaries:
                missing_binaries_count += 1
                for b in health.missing_binaries:
                    missing_binaries[b] += 1
            if health.missing_env_vars:
                missing_env_count += 1
                for env in health.missing_env_vars:
                    missing_env_vars[env] += 1
            if health.missing_modules:
                missing_python_count += 1

            if health.missing_env_vars and not health.missing_binaries:
                classification_counts["needs_api_credentials"] += 1
            elif health.missing_binaries:
                classification_counts["needs_external_binary"] += 1
            else:
                classification_counts["needs_dependency"] += 1

        # Test dry-run on first 50 skills or sample
        if i < 50 or (sample_limit and i < min(sample_limit, 50)):
            try:
                res = dispatcher.dispatch(
                    skill=skill,
                    context=base_context,
                )
                if res.success:
                    dry_run_successes += 1
                    if len(dry_run_samples) < 5:
                        dry_run_samples.append({
                            "id": skill.id,
                            "domain": skill.domain,
                            "dry_run_msg": res.stdout or "Valid execution workflow step",
                        })
                else:
                    dry_run_failures += 1
            except Exception as e:
                dry_run_failures += 1

        if (i + 1) % 500 == 0 or (i + 1) == len(all_skills):
            print(f"    - Processed {i + 1}/{len(all_skills)} skills...", flush=True)

    elapsed = time.monotonic() - start_time

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_skills_audited": len(all_skills),
        "total_library_skills": total_skills,
        "elapsed_seconds": round(elapsed, 2),
        "summary": {
            "ready_to_execute": ready_count,
            "needs_api_credentials": classification_counts["needs_api_credentials"],
            "needs_external_binary": classification_counts["needs_external_binary"],
            "needs_dependency": classification_counts["needs_dependency"],
            "dry_run_tested": dry_run_successes + dry_run_failures,
            "dry_run_successes": dry_run_successes,
            "dry_run_failures": dry_run_failures,
        },
        "top_domains": domain_counts.most_common(20),
        "top_required_env_vars": missing_env_vars.most_common(15),
        "top_required_binaries": missing_binaries.most_common(15),
        "sample_dry_runs": dry_run_samples,
    }

    print("\n" + "=" * 70, flush=True)
    print("VERIFICATION RESULTS SUMMARY", flush=True)
    print("=" * 70, flush=True)
    print(f"Total Skills Audited:       {report['total_skills_audited']}", flush=True)
    print(f"Audit Elapsed Time:         {report['elapsed_seconds']}s", flush=True)
    print(f"Skills Ready-To-Run:        {ready_count} ({ready_count/len(all_skills)*100:.1f}%)", flush=True)
    print(f"Skills Requiring API Keys:  {classification_counts['needs_api_credentials']}", flush=True)
    print(f"Skills Requiring Binaries:  {classification_counts['needs_external_binary']}", flush=True)
    print(f"Dry-Run Test Passes:        {dry_run_successes}/{dry_run_successes + dry_run_failures}", flush=True)
    print("\nTop Missing Env Vars (e.g. API Keys):", flush=True)
    for env, c in missing_env_vars.most_common(8):
        print(f"  - {env}: {c} skills", flush=True)
    print("\nTop Missing Binaries:", flush=True)
    for b, c in missing_binaries.most_common(8):
        print(f"  - {b}: {c} skills", flush=True)

    output_path = PROJECT_ROOT / "docs" / "SKILL_VERIFICATION_REPORT.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Full JSON report written to: {output_path}", flush=True)

    return report


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_batch_verification(limit)
