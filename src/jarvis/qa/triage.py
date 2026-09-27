"""AI triage for antibug findings, with a hard human gate on every change.

Design rule, learned the hard way in this repo: **the AI layer must never be
load-bearing for detection, and must never be able to modify source on its
own.**

Why detection is deterministic-first: the AI subsystem in this project was
silently dead (`openai` imported but never installed; every `_resolve()` branch
ended in `except: pass`). Had detection depended on the LLM, the bug finder
would have quietly reported "0 bugs" forever. So `bugscan` finds everything and
`LLMEngine` only ever adds commentary.

Why applying is human-gated: the working tree is shared with other in-flight
work, and an LLM rewriting files unattended would clobber it. Every patch this
module produces is a *proposal* that a human must approve by id.

Triage is strictly additive: if no provider resolves, every function here
reports that honestly and changes nothing. It never invents a fix.
"""

from __future__ import annotations

import difflib
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bugscan import Finding

TRIAGE_SYSTEM_PROMPT = (
    "You are a static-analysis reviewer for a Python codebase. You are given one "
    "finding produced by a deterministic rule. Explain the concrete runtime "
    "consequence in one or two sentences, then propose the smallest correct fix.\n"
    "Rules for your answer:\n"
    "- Be specific about when it fails and what the user observes.\n"
    "- If the finding is a false positive, say so plainly instead of inventing a fix.\n"
    "- Propose the minimal change; do not refactor surrounding code.\n"
    "- Output ONLY a unified diff, no prose, no markdown fences."
)


@dataclass
class Triage:
    """A finding plus optional AI commentary and a proposed patch."""

    finding: Finding
    #: "ok" when a provider resolved, or a reason the AI layer is unavailable.
    ai_status: str = "not_attempted"
    explanation: str = ""
    patch: str = ""
    model: str = ""
    reviewed: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding.finding_id,
            "rule": self.finding.rule,
            "severity": self.finding.severity,
            "file": self.finding.file,
            "line": self.finding.line,
            "message": self.finding.message,
            "snippet": self.finding.snippet,
            "ai_status": self.ai_status,
            "explanation": self.explanation,
            "model": self.model,
            "patch": self.patch,
            "reviewed": self.reviewed,
        }


def triage_one(finding: Finding, llm: Any | None = None) -> Triage:
    """Ask the LLM to explain one finding and propose a patch.

    Never raises for provider problems: an unavailable AI layer is a reported
    status, not an error. The finding is still fully actionable without it.
    """
    result = Triage(finding=finding)

    if llm is None:
        from jarvis.multimodal.jarvis_voice import LLMEngine

        llm = LLMEngine()

    try:
        llm._resolve()
    except Exception as exc:  # noqa: BLE001 - provider probing is best effort
        result.ai_status = f"provider probe failed: {type(exc).__name__}: {exc}"
        return result

    if getattr(llm, "_client", None) is None or getattr(llm, "_resolved_provider", "") == "offline":
        causes = "; ".join(getattr(llm, "resolve_errors", []) or [])
        result.ai_status = (
            "no LLM provider available; triage is deterministic-only. "
            f"Install a provider SDK to enable AI commentary. Causes: {causes or 'unknown'}"
        )
        return result

    prompt = (
        f"FINDING RULE: {finding.rule}\n"
        f"SEVERITY: {finding.severity}\n"
        f"FILE: {finding.file}\n"
        f"LINE: {finding.line}\n"
        f"CODE: {finding.snippet}\n"
        f"DETAIL: {finding.message}\n"
    )

    try:
        response = llm._client.chat.completions.create(
            model=getattr(llm, "_resolved_model", "") or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=800,
        )
        text = (response.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        result.ai_status = f"LLM call failed: {type(exc).__name__}: {exc}"
        return result

    result.model = getattr(llm, "_resolved_model", "")
    result.ai_status = "ok"
    diff, prose = _split_patch(text)
    result.patch = diff
    result.explanation = prose
    return result


def _split_patch(text: str) -> tuple[str, str]:
    """Separate a unified diff from any prose the model prefixed or appended."""
    text = text.replace("```diff", "").replace("```", "").strip()
    if not text:
        return "", ""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("--- ") or line.startswith("diff "):
            start = i
            break
    if start is None:
        return "", text
    patch = "\n".join(lines[start:]).strip()
    prose = "\n".join(lines[:start]).strip()
    return patch, prose


# ---------------------------------------------------------------------------
# gated application
# ---------------------------------------------------------------------------


@dataclass
class ApplyResult:
    ok: bool
    path: str
    message: str
    backup: str = ""
    diff: str = ""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def propose_apply(finding: Finding, triage: Triage, *, dry_run: bool = True) -> ApplyResult:
    """Show what applying a proposed patch would do. Never writes unless
    `dry_run=False`, and even then only for an explicitly reviewed triage.

    Verification is deliberately strict: a patch that does not compile is
    rejected outright. It is *not* applied to a file that fails `compile()`,
    because a syntax error introduced by a patch is worse than no patch.
    """
    if not triage.patch:
        return ApplyResult(
            ok=False,
            path=finding.file,
            message="no patch was proposed for this finding; nothing to apply",
        )

    root = _repo_root()
    target = (root / finding.file).resolve()
    if not str(target).startswith(str(root.resolve())):
        return ApplyResult(
            ok=False, path=finding.file,
            message="refusing to patch a path outside the repository",
        )
    if not target.is_file():
        return ApplyResult(ok=False, path=finding.file, message=f"file not found: {target}")

    original = target.read_text(encoding="utf-8")
    updated = _apply_unified_diff(original, triage.patch)
    if updated is None:
        return ApplyResult(
            ok=False, path=finding.file,
            message="patch did not apply cleanly to the current file; "
                    "it may be stale (the file changed after the scan). Re-scan and retry.",
        )
    if updated == original:
        return ApplyResult(
            ok=False, path=finding.file, message="patch produced no change"
        )

    try:
        compile(updated, str(target), "exec")
    except SyntaxError as exc:
        return ApplyResult(
            ok=False, path=finding.file,
            message=f"refusing to apply: the patched file would not compile ({exc.msg})",
            diff=_unified(original, updated, str(target)),
        )

    diff = _unified(original, updated, str(target))
    if dry_run:
        return ApplyResult(
            ok=True, path=finding.file,
            message="patch is applicable and compiles; re-run with --yes to write it",
            diff=diff,
        )

    backup = target.with_suffix(target.suffix + f".bak.{_stamp()}")
    shutil.copy2(target, backup)
    target.write_text(updated, encoding="utf-8")
    return ApplyResult(
        ok=True, path=finding.file, message="patch applied", backup=str(backup), diff=diff
    )


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _unified(before: str, after: str, label: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            before.splitlines(), after.splitlines(),
            fromfile=f"a/{label}", tofile=f"b/{label}", lineterm="",
        )
    )


def _apply_unified_diff(original: str, patch: str) -> str | None:
    """Apply a single-file unified diff. Returns None if any hunk misses.

    Deliberately minimal: one file, context lines must match exactly. An
    over-clever patcher is how a tool silently corrupts a file.
    """
    src = original.splitlines(keepends=True)
    out: list[str] = []
    idx = 0
    lines = patch.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- ") or line.startswith("+++ "):
            i += 1
            continue
        if not line.startswith("@@"):
            i += 1
            continue
        # @@ -old_start,old_count +new_start,new_count @@
        try:
            header = line.split("@@")[1].strip()
            old_part = header.split()[0]
            old_start = int(old_part.lstrip("-").split(",")[0]) - 1
        except (IndexError, ValueError):
            return None
        i += 1
        if old_start < idx or old_start > len(src):
            return None
        out.extend(src[idx:old_start])
        idx = old_start
        while i < len(lines) and not lines[i].startswith(("@@", "--- ")):
            hunk = lines[i]
            if hunk.startswith("+"):
                out.append(hunk[1:] + "\n")
            elif hunk.startswith("-"):
                if idx >= len(src) or src[idx].rstrip("\r\n") != hunk[1:]:
                    return None
                idx += 1
            elif hunk.startswith(" "):
                if idx >= len(src) or src[idx].rstrip("\r\n") != hunk[1:]:
                    return None
                out.append(src[idx])
                idx += 1
            elif hunk.startswith("\\"):
                pass
            else:
                break
            i += 1
    out.extend(src[idx:])
    return "".join(out)
