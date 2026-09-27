from __future__ import annotations

"""JARVIS 2.0 Autonomous Cognitive Agent & Skill Operator (spec §20, §M5, §M7).

Transforms JARVIS from a reactive pattern matcher into an autonomous, tool-using
cognitive agent. Bridges the LLM Brain (Gemini / Groq / OpenAI) with:
1. The 2,400+ Skill Library (SkillRegistry, SkillRuntimeEngine, SkillDispatcher)
2. Native OS Command Execution (PowerShell / Windows API)
3. Direct Filesystem Operations (Read / Write / Search)
4. Desktop & Computer-Use Controls (M7.2 / M7.5)
5. Cryptographic Event Log & Semantic Memory Kernel
6. Web Search and Live Telemetry Retrieval
"""

import json
import logging
import os
import hashlib
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from jarvis.kernel.event_log import Event, EventLog
from jarvis.multimodal.jarvis_voice import (
    ConversationMemory,
    JARVIS_SYSTEM_PROMPT,
    LLMEngine,
    get_live_system_context,
    sanitize_speech_text,
)
from jarvis.personal import PersonalIntelligenceEngine, get_personal_intelligence
from jarvis.skills.context import SkillExecutionContext
from jarvis.skills.dispatcher import SkillDispatcher, SkillExecutionResult
from jarvis.skills.engine import SkillGoalResult, SkillRuntimeEngine
from jarvis.skills.manifest import SkillManifest
from jarvis.skills.registry import SkillMatch, SkillRegistry, get_default_registry

logger = logging.getLogger("jarvis.skills.cognitive_agent")

COGNITIVE_SYSTEM_PROMPT = f"""{JARVIS_SYSTEM_PROMPT}

[COGNITIVE OPERATING SYSTEM DIRECTIVES]
You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the autonomous spatial desktop companion and persistent cognitive operating system.
You are equipped with real, executable hands on this Windows workstation:
1. Over 2,400 registered skills in your skill library (`execute_skill`, `find_skills`).
2. Native Windows command execution via PowerShell (`run_system_command`).
3. Direct filesystem manipulation (`filesystem_operation`).
4. Physical desktop & media controls (`system_control`).
5. Live web search and information retrieval (`web_search`).
6. Append-only cryptographic memory storage and recall (`memory_operation`).
7. Desktop GUI and window interaction (`computer_use`).

[CRITICAL BEHAVIOR RULES]
- You are an ACTIVE AUTONOMOUS AGENT, not a passive chatbot.
- If the user asks you to inspect the computer, check disk/RAM/CPU, manage files, kill tasks, run scripts, look up information, or execute a task:
  YOU MUST EXECUTE THE APPROPRIATE TOOL IMMEDIATELY. Never say "I can help with that" or "You can run this command" without executing it yourself.
- When a tool returns output, inspect the results and report the verified findings concisely and elegantly to the user.
- Always address the user politely as 'sir'. Maintain the calm, witty, brilliant, and impeccably capable British persona of Paul Bettany.
- Keep final spoken responses concise, punchy, and clear so they sound natural when spoken aloud.
"""

AGENT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "run_system_command",
            "description": "Execute a command on the user's Windows system (PowerShell or CMD) to inspect system state, query files, manage processes, check network, get hardware stats, etc. Use this whenever the user asks for system inspection, running scripts, or command-line operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact PowerShell command to execute.",
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Optional working directory path.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_skill",
            "description": "Execute a specialized skill from the JARVIS library of 2,400+ skills by skill ID or goal. Runs with deterministic isolation and safety gating.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_id": {
                        "type": "string",
                        "description": "The unique ID of the skill (e.g. 'sysdiag-disk', 'sysdiag-cpu', 'files-search', 'netadmin-disk-usage').",
                    },
                    "goal": {
                        "type": "string",
                        "description": "High-level goal or instruction for the skill.",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Key-value dictionary of parameters for the skill.",
                    },
                },
                "required": ["skill_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_skills",
            "description": "Search the JARVIS skill library to find available skills matching a keyword, domain, or capability (e.g. 'disk', 'cpu', 'weather', 'crypto', 'photo', 'network').",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query or keywords.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of skills to return (default 5).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filesystem_operation",
            "description": "Directly interact with the local filesystem: read file contents, write text files, list directory contents, or create directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["read_file", "write_file", "list_dir", "make_dir"],
                        "description": "The filesystem action to perform.",
                    },
                    "path": {
                        "type": "string",
                        "description": "The path to the target file or directory.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write when operation is 'write_file'.",
                    },
                },
                "required": ["operation", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_control",
            "description": "Control system hardware, audio, and desktop window state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "volume_up",
                            "volume_down",
                            "mute_toggle",
                            "media_play_pause",
                            "media_next",
                            "media_prev",
                            "lock_workstation",
                            "minimize_all",
                            "launch_app",
                            "open_url",
                        ],
                        "description": "The system action to trigger.",
                    },
                    "target": {
                        "type": "string",
                        "description": "Application name, executable, or URL (for launch_app / open_url).",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web or fetch live information from online sources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The web search query.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_operation",
            "description": "Store a permanent fact in JARVIS's append-only cryptographic memory or recall past stored knowledge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["remember", "recall"],
                        "description": "Whether to store ('remember') or query ('recall') memory.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The fact to remember or the query to search.",
                    },
                },
                "required": ["operation", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "learn_skill",
            "description": "Synthesize, persist, and register a brand new skill in JARVIS's skill library on-the-fly. Use this whenever the user asks JARVIS to learn how to do something, automate a new task, or create a custom procedure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Unique identifier in kebab-case (e.g. 'dev-clean-pycache', 'sysdiag-battery-health').",
                    },
                    "description": {
                        "type": "string",
                        "description": "Clear explanation of what the skill does and when to activate it.",
                    },
                    "language": {
                        "type": "string",
                        "enum": ["powershell", "python", "bash", "cmd"],
                        "description": "Scripting language for execution.",
                    },
                    "code": {
                        "type": "string",
                        "description": "Executable script/code to run when this skill is invoked.",
                    },
                    "triggers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of natural language trigger phrases.",
                    },
                },
                "required": ["skill_name", "description", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_automation",
            "description": "Create a scheduled recurring or delayed background automation task (e.g. system maintenance, periodic checks, cleanup routines).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Descriptive name for the automation.",
                    },
                    "goal": {
                        "type": "string",
                        "description": "The exact command or goal to execute periodically.",
                    },
                    "interval_seconds": {
                        "type": "number",
                        "description": "Execution interval in seconds (e.g., 3600 for hourly).",
                    },
                    "max_runs": {
                        "type": "integer",
                        "description": "Optional maximum number of runs (omit for indefinite).",
                    },
                },
                "required": ["name", "goal", "interval_seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "desktop_input",
            "description": "Control the physical mouse cursor and keyboard: move the mouse to coordinates (x, y), click, double-click, right-click, type text, press keyboard shortcuts, or scroll.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["move_mouse", "click", "double_click", "right_click", "type_text", "press_key", "scroll", "get_cursor_pos"],
                        "description": "The desktop hardware action to perform.",
                    },
                    "x": {"type": "integer", "description": "X coordinate in screen pixels."},
                    "y": {"type": "integer", "description": "Y coordinate in screen pixels."},
                    "text": {"type": "string", "description": "Text to type into the active window."},
                    "key": {"type": "string", "description": "Key name or shortcut (e.g. 'enter', 'tab', 'esc', 'win', 'ctrl+c', 'alt+tab')."},
                    "scroll_delta": {"type": "integer", "description": "Scroll wheel clicks (positive up, negative down)."},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screen_perception",
            "description": "Perceive the user's screen visually and interact with UI elements without needing coordinates: inspect the active window, list visible open applications with their bounding boxes, locate buttons/windows by title or text, and click or focus them automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["inspect_screen", "find_and_click", "find_and_focus", "find_and_type"],
                        "description": "Perception action to execute.",
                    },
                    "target": {
                        "type": "string",
                        "description": "The name, title, or label of the window or UI element (e.g. 'Notepad', 'Chrome', 'Visual Studio Code', 'Save').",
                    },
                    "text": {
                        "type": "string",
                        "description": "Optional text to type if action is 'find_and_type'.",
                    },
                },
                "required": ["action"],
            },
        },
    },
]


@dataclass
class ToolExecutionRecord:
    """Record of a single tool execution during an agent turn."""

    name: str
    args: dict[str, Any]
    output: Any
    success: bool
    duration_ms: float


@dataclass
class AgentTurnResult:
    """Result of processing a user utterance through the Cognitive Agent."""

    reply: str
    action: str
    tools_executed: list[ToolExecutionRecord] = field(default_factory=list)
    success: bool = True
    error: str | None = None


class CognitiveAgent:
    """Autonomous Cognitive Agent orchestrating LLM reasoning and system tools."""

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        skill_engine: SkillRuntimeEngine | None = None,
        llm_engine: LLMEngine | None = None,
        event_log: EventLog | None = None,
        authority: Any | None = None,
        learn_grant: Any | None = None,
        personal_intelligence: PersonalIntelligenceEngine | None = None,
    ) -> None:
        self.registry = registry or get_default_registry()
        self.event_log = event_log
        self.authority = authority
        self.learn_grant = learn_grant
        self.skill_engine = skill_engine or SkillRuntimeEngine(
            registry=self.registry,
            event_sink=event_log,
        )
        self.llm_engine = llm_engine or LLMEngine()
        self.memory = ConversationMemory(max_turns=16)
        self.personal_intelligence = personal_intelligence or get_personal_intelligence()

    def execute_tool(self, name: str, args: dict[str, Any]) -> tuple[Any, bool]:
        """Execute a concrete tool call deterministically."""
        start_time = time.perf_counter()
        try:
            if name == "run_system_command":
                cmd = args.get("command", "")
                cwd = args.get("working_directory") or os.getcwd()
                if not cmd:
                    return {"error": "No command provided"}, False

                shell_type = args.get("shell", "auto")
                lowered_cmd = cmd.strip().lower()
                is_cmd = False
                if shell_type == "cmd":
                    is_cmd = True
                elif shell_type == "auto" and sys.platform == "win32":
                    if lowered_cmd.startswith(("cmd ", "cmd.exe ", "dir /", "dir", "type ", "copy ", "move ", "del /", "del ")):
                        is_cmd = True

                # Safe execution with background priority
                kwargs: dict[str, Any] = {
                    "cwd": cwd,
                    "capture_output": True,
                    "text": True,
                    "timeout": 25.0,
                }
                if sys.platform == "win32":
                    kwargs["creationflags"] = (
                        getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0x00004000)
                        | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                    )

                if is_cmd and sys.platform == "win32":
                    actual_cmd = cmd
                    if lowered_cmd.startswith("cmd.exe /c "):
                        actual_cmd = cmd[11:]
                    elif lowered_cmd.startswith("cmd /c "):
                        actual_cmd = cmd[7:]
                    runner_argv = ["cmd.exe", "/c", actual_cmd]
                else:
                    runner_argv = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd]

                res = subprocess.run(runner_argv, **kwargs)
                stdout = res.stdout.strip()
                stderr = res.stderr.strip()
                out = {
                    "exit_code": res.returncode,
                    "stdout": stdout[:4000] if stdout else "",
                    "stderr": stderr[:1000] if stderr else "",
                }
                return out, res.returncode == 0

            elif name == "find_skills":
                query = args.get("query", "")
                limit = int(args.get("limit", 5))
                matches = self.registry.find(query, limit=limit)
                out = [
                    {
                        "id": m.skill.id,
                        "title": m.skill.title or m.skill.name,
                        "domain": m.skill.domain,
                        "description": m.skill.description,
                        "triggers": m.skill.triggers[:3],
                    }
                    for m in matches
                ]
                return {"count": len(out), "skills": out}, True

            elif name == "execute_skill":
                skill_id = args.get("skill_id", "")
                goal = args.get("goal") or f"Execute {skill_id}"
                params = args.get("parameters") or {}

                ctx = SkillExecutionContext(
                    workspace=Path.cwd() / "artifacts",
                    parameters=params,
                    timeout_seconds=30.0,
                )
                skill = self.registry.get(skill_id)
                if skill is None:
                    # Try resolving by goal
                    res = self.skill_engine.execute_goal(goal, ctx)
                else:
                    # Dispatch directly
                    exec_res = self.skill_engine.dispatcher.dispatch(skill, ctx)
                    res = SkillGoalResult(
                        goal=goal,
                        selected_skill=skill,
                        execution=exec_res,
                        health=None,
                        success=exec_res.success,
                        status="SUCCEEDED" if exec_res.success else "EXECUTION_FAILED",
                        message=exec_res.stdout or exec_res.error or "",
                    )

                out = {
                    "skill_id": skill_id,
                    "success": res.success,
                    "status": res.status,
                    "output": res.execution.stdout.strip() if res.execution and res.execution.stdout else res.message,
                    "error": res.execution.error if res.execution and not res.success else None,
                }
                return out, res.success

            elif name == "filesystem_operation":
                op = args.get("operation")
                path_str = args.get("path", "")
                content = args.get("content", "")
                p = Path(path_str).expanduser().resolve()

                if op == "read_file":
                    if not p.is_file():
                        return {"error": f"File does not exist: {p}"}, False
                    text = p.read_text(encoding="utf-8", errors="replace")
                    return {"path": str(p), "size_bytes": len(text), "content": text[:8000]}, True

                elif op == "write_file":
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(content, encoding="utf-8")
                    return {"path": str(p), "written_bytes": len(content), "status": "written"}, True

                elif op == "list_dir":
                    if not p.is_dir():
                        return {"error": f"Not a directory: {p}"}, False
                    items = []
                    for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:50]:
                        items.append({
                            "name": child.name,
                            "is_dir": child.is_dir(),
                            "size_bytes": child.stat().st_size if child.is_file() else None,
                        })
                    return {"path": str(p), "total_listed": len(items), "items": items}, True

                elif op == "make_dir":
                    p.mkdir(parents=True, exist_ok=True)
                    return {"path": str(p), "status": "created"}, True

                return {"error": f"Unknown filesystem operation: {op}"}, False

            elif name == "system_control":
                action = args.get("action", "")
                target = args.get("target", "")

                if sys.platform == "win32":
                    import ctypes

                    def _send_vk(vk_code: int) -> None:
                        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
                        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)

                    if action == "volume_up":
                        for _ in range(5):
                            _send_vk(0xAF)
                        return {"action": action, "status": "volume increased"}, True

                    elif action == "volume_down":
                        for _ in range(5):
                            _send_vk(0xAE)
                        return {"action": action, "status": "volume decreased"}, True

                    elif action == "mute_toggle":
                        _send_vk(0xAD)
                        return {"action": action, "status": "mute toggled"}, True

                    elif action == "media_play_pause":
                        _send_vk(0xB3)
                        return {"action": action, "status": "playback toggled"}, True

                    elif action == "media_next":
                        _send_vk(0xB0)
                        return {"action": action, "status": "skipped to next track"}, True

                    elif action == "media_prev":
                        _send_vk(0xB1)
                        return {"action": action, "status": "returned to previous track"}, True

                    elif action == "lock_workstation":
                        ctypes.windll.user32.LockWorkStation()
                        return {"action": action, "status": "workstation locked"}, True

                    elif action == "minimize_all":
                        ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
                        ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)
                        ctypes.windll.user32.keybd_event(0x44, 0, 2, 0)
                        ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)
                        return {"action": action, "status": "windows minimized"}, True

                    elif action == "launch_app":
                        os.system(f'start "" "{target}"')
                        return {"action": action, "target": target, "status": "launched"}, True

                    elif action == "open_url":
                        import webbrowser
                        webbrowser.open(target)
                        return {"action": action, "url": target, "status": "opened"}, True

                return {"error": f"Unsupported action or platform: {action}"}, False

            elif name == "web_search":
                query = args.get("query", "")
                import urllib.parse
                import urllib.request
                encoded = urllib.parse.quote_plus(query)
                # Query DuckDuckGo instant answer API
                api_url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
                try:
                    req = urllib.request.Request(api_url, headers={"User-Agent": "JARVIS/2.0"})
                    with urllib.request.urlopen(req, timeout=4.0) as resp:
                        data = json.loads(resp.read().decode())
                        abstract = data.get("AbstractText", "")
                        heading = data.get("Heading", "")
                        related = [
                            t.get("Text")
                            for t in data.get("RelatedTopics", [])
                            if isinstance(t, dict) and t.get("Text")
                        ][:3]
                    if not abstract:
                        # Fallback to Wikipedia search API for detailed encyclopedia facts
                        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded}&format=json&utf8=1"
                        wreq = urllib.request.Request(wiki_url, headers={"User-Agent": "JARVIS/2.0"})
                        try:
                            with urllib.request.urlopen(wreq, timeout=3.0) as wresp:
                                wdata = json.loads(wresp.read().decode())
                                search_results = wdata.get("query", {}).get("search", [])
                                if search_results:
                                    snippets = [
                                        re.sub(r"<[^>]+>", "", s.get("snippet", "")).strip()
                                        for s in search_results[:3]
                                    ]
                                    abstract = " | ".join(snippets)
                        except Exception:
                            pass

                    return {
                        "query": query,
                        "heading": heading,
                        "abstract": abstract or "No instant abstract available.",
                        "related": related,
                    }, True
                except Exception as ex:
                    return {"query": query, "status": "search_failed", "error": str(ex)}, False

            elif name == "memory_operation":
                op = args.get("operation")
                content = args.get("content", "")
                if op == "remember":
                    if self.event_log:
                        self.event_log.audit(
                            stream_id="companion",
                            event_type="memory_saved",
                            principal_id="cognitive_agent",
                            payload={"fact": content, "timestamp": time.time()},
                        )
                    return {"status": "saved", "fact": content}, True
                elif op == "recall":
                    # Query event log for matching memories
                    matches = []
                    if self.event_log:
                        for ev in self.event_log.replay(stream_id="companion"):
                            if ev.event_type == "memory_saved" and content.lower() in json.dumps(ev.payload).lower():
                                matches.append(ev.payload.get("fact"))
                    return {"query": content, "matches": matches[:5]}, True

            elif name == "learn_skill":
                raw_name = args.get("skill_name", "").strip().lower()
                clean_name = re.sub(r"[^a-z0-9_-]", "-", raw_name).strip("-")
                if not clean_name:
                    return {"error": "Invalid skill_name provided"}, False

                description = args.get("description", "").strip() or "Custom user-taught skill."
                code = args.get("code", "").strip()
                lang = args.get("language", "powershell").lower()
                triggers = args.get("triggers") or [clean_name.replace("-", " ")]

                # ---- ADR-011 S2: learning is allowed, running is not ------
                # Revision note: S2 originally demanded an Ed25519 `skill_learn`
                # grant. That was theater and is removed. The agent holds
                # `run_system_command` and `filesystem_operation`, so it can
                # (a) write `.agents/skills/<n>/SKILL.md` directly, bypassing
                # this function entirely, and (b) shell out to `jarvis grant`,
                # which signs with the very key in its own `$JARVIS_HOME`. A
                # signature over a payload the subject can produce at will
                # proves nothing about who authorized it.
                #
                # What is actually enforced, and where the boundary really sits:
                # writing a SKILL.md is a FILE WRITE, not a capability. A written
                # skill is inert until it passes S4's execution allowlist, and
                # S4 is evaluated at dispatch time against the file, not against
                # how the file arrived. So the honest rule is: learn freely,
                # execute only what a human has reviewed and admitted.
                #
                # The digest is still computed and journalled, as an audit
                # artifact identifying WHAT was written - not as proof of WHO
                # wrote it.
                if not code:
                    return {"error": "Refusing to learn a skill with empty code."}, False

                code_sha256 = hashlib.sha256(code.encode("utf-8")).hexdigest()

                trigger_bullets = "\n".join(f"- \"{t}\"" for t in triggers)
                md_content = f"""---
name: {clean_name}
description: {description}
---

# {clean_name.replace('-', ' ').title()}

## Purpose
{description}

## When to Activate
{trigger_bullets}

## Workflow
```{lang}
{code}
```
"""
                skill_dir = Path(".agents/skills") / clean_name
                skill_dir.mkdir(parents=True, exist_ok=True)
                skill_file = skill_dir / "SKILL.md"
                skill_file.write_text(md_content, encoding="utf-8")

                # Register in live SkillRegistry
                from jarvis.skills.manifest import SkillManifest
                manifest = SkillManifest.load(skill_dir)
                if manifest:
                    self.registry.register(manifest)

                # Journal the acquisition. Writing a skill is a file write, but
                # the file is EXECUTABLE CODE once admitted, so the ledger must
                # record what landed: which skill, which digest, and explicitly
                # that it is not yet runnable. Previously this was
                # `append(stream_id=...)` (a TypeError) inside
                # `except Exception: pass`, so `skill.learned` never reached the
                # ledger at all.
                if self.event_log:
                    self.event_log.audit(
                        stream_id="skills",
                        event_type="skill.learned",
                        principal_id="cognitive_agent",
                        payload={
                            "skill_id": clean_name,
                            "description": description,
                            "path": str(skill_file),
                            "language": lang,
                            "code_sha256": code_sha256,
                            "executable": False,
                            "note": (
                                "written to disk; inert until admitted to the "
                                "execution allowlist (ADR-011 S4)"
                            ),
                        },
                    )

                return {
                    "status": "learned",
                    "skill_id": clean_name,
                    "file": str(skill_file),
                    "registered": manifest is not None,
                    "code_sha256": code_sha256,
                    "executable": False,
                    "next_step": (
                        f"review it, then run: jarvis skill admit {clean_name}"
                    ),
                }, True

            elif name == "create_automation":
                auto_name = args.get("name", "Unnamed Automation").strip()
                goal = args.get("goal", "").strip()
                interval = float(args.get("interval_seconds", 3600))
                max_runs = args.get("max_runs")

                auto_dir = Path("artifacts/automations")
                auto_dir.mkdir(parents=True, exist_ok=True)
                auto_id = f"auto_{int(time.time())}_{re.sub(r'[^a-z0-9]', '_', auto_name.lower())[:20]}"
                auto_spec = {
                    "automation_id": auto_id,
                    "name": auto_name,
                    "goal": goal,
                    "interval_seconds": interval,
                    "max_runs": max_runs,
                    "created_at": time.time(),
                    "enabled": True,
                }
                auto_file = auto_dir / f"{auto_id}.json"
                auto_file.write_text(json.dumps(auto_spec, indent=2), encoding="utf-8")

                if self.event_log:
                    self.event_log.audit(
                        stream_id="scheduler",
                        event_type="automation.created",
                        principal_id="cognitive_agent",
                        payload=auto_spec,
                    )

                return {
                    "status": "created",
                    "automation_id": auto_id,
                    "name": auto_name,
                    "interval_seconds": interval,
                    "path": str(auto_file),
                }, True

            elif name == "desktop_input":
                action = args.get("action", "")
                if sys.platform != "win32":
                    return {"error": "Desktop input emulation requires Windows."}, False

                import ctypes, ctypes.wintypes
                user32 = ctypes.windll.user32

                if action == "get_cursor_pos":
                    pt = ctypes.wintypes.POINT()
                    user32.GetCursorPos(ctypes.byref(pt))
                    return {"x": pt.x, "y": pt.y}, True

                elif action == "move_mouse":
                    x = int(args.get("x", 0))
                    y = int(args.get("y", 0))
                    user32.SetCursorPos(x, y)
                    sm_cx = user32.GetSystemMetrics(0) or 1920
                    sm_cy = user32.GetSystemMetrics(1) or 1080
                    nx = int(x * 65535 / sm_cx)
                    ny = int(y * 65535 / sm_cy)
                    user32.mouse_event(0x8001, nx, ny, 0, 0)
                    return {"action": "move_mouse", "x": x, "y": y, "success": True}, True

                elif action in ("click", "double_click", "right_click"):
                    x = args.get("x")
                    y = args.get("y")
                    if x is not None and y is not None:
                        ix, iy = int(x), int(y)
                        user32.SetCursorPos(ix, iy)
                        sm_cx = user32.GetSystemMetrics(0) or 1920
                        sm_cy = user32.GetSystemMetrics(1) or 1080
                        nx = int(ix * 65535 / sm_cx)
                        ny = int(iy * 65535 / sm_cy)
                        user32.mouse_event(0x8001, nx, ny, 0, 0)
                        time.sleep(0.05)

                    if action == "click":
                        user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
                        time.sleep(0.02)
                        user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
                    elif action == "double_click":
                        for _ in range(2):
                            user32.mouse_event(0x0002, 0, 0, 0, 0)
                            time.sleep(0.02)
                            user32.mouse_event(0x0004, 0, 0, 0, 0)
                            time.sleep(0.05)
                    elif action == "right_click":
                        user32.mouse_event(0x0008, 0, 0, 0, 0)  # RIGHTDOWN
                        time.sleep(0.02)
                        user32.mouse_event(0x0010, 0, 0, 0, 0)  # RIGHTUP

                    return {"action": action, "x": x, "y": y, "status": "clicked"}, True

                elif action == "scroll":
                    delta = int(args.get("scroll_delta", -120))
                    user32.mouse_event(0x0800, 0, 0, delta, 0)  # MOUSEEVENTF_WHEEL
                    return {"action": "scroll", "delta": delta, "status": "scrolled"}, True

                elif action == "type_text":
                    text_to_type = args.get("text", "")
                    for char in text_to_type:
                        user32.keybd_event(0, ord(char), 0x0004, 0)
                        user32.keybd_event(0, ord(char), 0x0004 | 0x0002, 0)
                        time.sleep(0.01)
                    return {"action": "type_text", "length": len(text_to_type), "status": "typed"}, True

                elif action == "press_key":
                    key_name = args.get("key", "").lower().strip()
                    KEY_MAP = {
                        "enter": 0x0D, "return": 0x0D,
                        "tab": 0x09, "space": 0x20, "esc": 0x1B, "escape": 0x1B,
                        "backspace": 0x08, "win": 0x5B, "windows": 0x5B,
                        "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
                        "delete": 0x2E, "home": 0x24, "end": 0x23,
                    }
                    if "+" in key_name:
                        modifiers = []
                        parts = [p.strip() for p in key_name.split("+")]
                        main_key = parts[-1]
                        for m in parts[:-1]:
                            if m in ("ctrl", "control"):
                                modifiers.append(0x11)
                            elif m == "alt":
                                modifiers.append(0x12)
                            elif m == "shift":
                                modifiers.append(0x10)
                            elif m in ("win", "windows"):
                                modifiers.append(0x5B)

                        for mod in modifiers:
                            user32.keybd_event(mod, 0, 0, 0)

                        main_vk = KEY_MAP.get(main_key) or (ord(main_key.upper()) if len(main_key) == 1 else 0)
                        if main_vk:
                            user32.keybd_event(main_vk, 0, 0, 0)
                            time.sleep(0.02)
                            user32.keybd_event(main_vk, 0, 2, 0)

                        for mod in reversed(modifiers):
                            user32.keybd_event(mod, 0, 2, 0)

                        return {"action": "press_key", "shortcut": key_name, "status": "pressed"}, True
                    else:
                        vk = KEY_MAP.get(key_name) or (ord(key_name.upper()) if len(key_name) == 1 else 0)
                        if vk:
                            user32.keybd_event(vk, 0, 0, 0)
                            time.sleep(0.02)
                            user32.keybd_event(vk, 0, 2, 0)
                            return {"action": "press_key", "key": key_name, "status": "pressed"}, True
                        return {"error": f"Unknown key: {key_name}"}, False

                return {"error": f"Unknown desktop_input action: {action}"}, False

            elif name == "screen_perception":
                action = args.get("action", "inspect_screen")
                target = args.get("target", "").lower().strip()
                text_to_type = args.get("text", "")

                if sys.platform != "win32":
                    return {"error": "Screen perception requires Windows."}, False

                import ctypes, ctypes.wintypes
                user32 = ctypes.windll.user32

                windows: list[dict[str, Any]] = []

                def _enum_windows_callback(hwnd, extra):
                    if user32.IsWindowVisible(hwnd):
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buff, length + 1)
                            title = buff.value
                            rect = ctypes.wintypes.RECT()
                            user32.GetWindowRect(hwnd, ctypes.byref(rect))
                            width = rect.right - rect.left
                            height = rect.bottom - rect.top
                            if width > 100 and height > 80:
                                windows.append({
                                    "hwnd": hwnd,
                                    "title": title,
                                    "left": rect.left,
                                    "top": rect.top,
                                    "right": rect.right,
                                    "bottom": rect.bottom,
                                    "center_x": rect.left + width // 2,
                                    "center_y": rect.top + height // 2,
                                    "width": width,
                                    "height": height,
                                })
                    return True

                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
                user32.EnumWindows(EnumWindowsProc(_enum_windows_callback), 0)

                def _get_child_controls(parent_hwnd: int) -> list[dict[str, Any]]:
                    controls: list[dict[str, Any]] = []
                    def _child_cb(hwnd, _):
                        if user32.IsWindowVisible(hwnd):
                            rect = ctypes.wintypes.RECT()
                            user32.GetWindowRect(hwnd, ctypes.byref(rect))
                            cw = rect.right - rect.left
                            ch = rect.bottom - rect.top
                            if cw >= 8 and ch >= 8:
                                tlen = user32.GetWindowTextLengthW(hwnd)
                                ctitle = ""
                                if tlen > 0:
                                    cbuff = ctypes.create_unicode_buffer(tlen + 1)
                                    user32.GetWindowTextW(hwnd, cbuff, tlen + 1)
                                    ctitle = cbuff.value.strip()
                                clsbuff = ctypes.create_unicode_buffer(128)
                                user32.GetClassNameW(hwnd, clsbuff, 128)
                                cclass = clsbuff.value.strip()
                                if ctitle or cclass in ("Button", "Edit", "ComboBox", "Static"):
                                    controls.append({
                                        "hwnd": hwnd,
                                        "title": ctitle,
                                        "class": cclass,
                                        "center_x": rect.left + cw // 2,
                                        "center_y": rect.top + ch // 2,
                                        "width": cw,
                                        "height": ch,
                                    })
                        return True
                    user32.EnumChildWindows(parent_hwnd, EnumWindowsProc(_child_cb), 0)
                    return controls

                fg_hwnd = user32.GetForegroundWindow()
                fg_title = ""
                fg_length = user32.GetWindowTextLengthW(fg_hwnd)
                if fg_length > 0:
                    fg_buff = ctypes.create_unicode_buffer(fg_length + 1)
                    user32.GetWindowTextW(fg_hwnd, fg_buff, fg_length + 1)
                    fg_title = fg_buff.value

                res_width = user32.GetSystemMetrics(0)
                res_height = user32.GetSystemMetrics(1)

                if action == "inspect_screen":
                    primary_hwnd = fg_hwnd or (windows[0]["hwnd"] if windows else 0)
                    active_controls = []
                    if primary_hwnd:
                        active_controls = [c["title"] for c in _get_child_controls(primary_hwnd) if c["title"]][:15]
                    return {
                        "resolution": f"{res_width}x{res_height}",
                        "active_window": fg_title or (windows[0]["title"] if windows else "Desktop"),
                        "visible_windows": [w["title"] for w in windows[:12]],
                        "window_count": len(windows),
                        "active_window_controls": active_controls,
                    }, True

                elif action in ("find_and_click", "find_and_focus", "find_and_type"):
                    if not target:
                        return {"error": "Target element or window title must be specified."}, False

                    # 1. First, check if target matches a child button/control in active foreground window
                    active_parent = fg_hwnd or (windows[0]["hwnd"] if windows else 0)
                    matched_control = None
                    if active_parent:
                        for ctrl in _get_child_controls(active_parent):
                            if ctrl["title"] and target in ctrl["title"].lower():
                                matched_control = ctrl
                                break

                    if matched_control:
                        cx, cy = matched_control["center_x"], matched_control["center_y"]
                        user32.SetCursorPos(cx, cy)
                        sm_cx = user32.GetSystemMetrics(0) or 1920
                        sm_cy = user32.GetSystemMetrics(1) or 1080
                        nx = int(cx * 65535 / sm_cx)
                        ny = int(cy * 65535 / sm_cy)
                        user32.mouse_event(0x8001, nx, ny, 0, 0)
                        user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
                        time.sleep(0.02)
                        user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
                        if action == "find_and_type" and text_to_type:
                            time.sleep(0.05)
                            for char in text_to_type:
                                user32.keybd_event(0, ord(char), 0x0004, 0)
                                user32.keybd_event(0, ord(char), 0x0004 | 0x0002, 0)
                                time.sleep(0.01)
                        return {
                            "action": action,
                            "target": matched_control["title"] or matched_control["class"],
                            "element_type": "child_control",
                            "coordinates": (cx, cy),
                            "status": "clicked control" if action != "find_and_type" else "clicked control and typed",
                        }, True

                    # 2. Match against visible top-level windows
                    matched_win = None
                    for w in windows:
                        if target in w["title"].lower():
                            matched_win = w
                            break

                    if not matched_win:
                        return {
                            "error": f"Target '{target}' not found among visible windows or controls.",
                            "visible_windows": [w["title"] for w in windows[:8]],
                        }, False

                    hwnd = matched_win["hwnd"]
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    user32.SetForegroundWindow(hwnd)
                    time.sleep(0.08)

                    # Check if target window has an edit/input control for typing
                    cx, cy = matched_win["center_x"], matched_win["center_y"]
                    if action == "find_and_type":
                        win_controls = _get_child_controls(hwnd)
                        edit_ctrl = next((c for c in win_controls if c["class"] == "Edit"), None)
                        if edit_ctrl:
                            cx, cy = edit_ctrl["center_x"], edit_ctrl["center_y"]

                    if action in ("find_and_click", "find_and_type"):
                        user32.SetCursorPos(cx, cy)
                        sm_cx = user32.GetSystemMetrics(0) or 1920
                        sm_cy = user32.GetSystemMetrics(1) or 1080
                        nx = int(cx * 65535 / sm_cx)
                        ny = int(cy * 65535 / sm_cy)
                        user32.mouse_event(0x8001, nx, ny, 0, 0)
                        user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
                        time.sleep(0.02)
                        user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP

                    if action == "find_and_type" and text_to_type:
                        time.sleep(0.05)
                        for char in text_to_type:
                            user32.keybd_event(0, ord(char), 0x0004, 0)
                            user32.keybd_event(0, ord(char), 0x0004 | 0x0002, 0)
                            time.sleep(0.01)

                    return {
                        "action": action,
                        "target": matched_win["title"],
                        "element_type": "window",
                        "coordinates": (cx, cy),
                        "status": "focused and clicked" if action != "find_and_type" else "focused, clicked, and typed",
                    }, True

                return {"error": f"Unknown screen_perception action: {action}"}, False

            return {"error": f"Unknown tool: {name}"}, False

        except Exception as exc:
            logger.exception("Error executing tool %s", name)
            return {"error": str(exc)}, False

    def process_turn(
        self,
        user_input: str,
        source: str = "desktop_app",
        max_tool_iterations: int = 5,
    ) -> AgentTurnResult:
        """Process a user turn with intelligent multi-turn tool calling."""
        text = user_input.strip()
        if not text:
            return AgentTurnResult(reply="I am listening, sir.", action="idle", success=True)
        lowered = text.lower()

        # Dynamic creator profile & personal intelligence learning
        learn_note = self.personal_intelligence.process_user_turn_for_learning(text)
        is_personal_stmt = any(
            lowered.startswith(p)
            for p in (
                "call me ",
                "my name is ",
                "i like ",
                "i really like ",
                "i love ",
                "i really love ",
                "i prefer ",
                "my favorite ",
                "i am tired",
                "i'm tired",
                "exhausted",
            )
        )
        if is_personal_stmt and learn_note:
            return AgentTurnResult(
                reply=learn_note,
                action="personal_intelligence_learned",
                success=True,
            )

        # Log turn to WAL EventLog if available
        if self.event_log:
            self.event_log.audit(
                stream_id="companion",
                event_type="dialogue_turn",
                principal_id="cognitive_agent",
                payload={"text": text, "source": source},
            )

        # Direct deterministic execution shortcuts (cmd:, powershell:, mouse:, key:, type:, learn:, multi-step, vision)
        direct_prefixes = ("cmd:", "run:", "powershell:", "ps:", "exec:", "learn:", "teach:", "skill:", "mouse:", "type:", "key:", "inspect screen", "look at screen", "see screen")
        if any(text.lower().startswith(p) for p in direct_prefixes) or " and then " in text.lower() or " then " in text.lower() or (";" in text and len(text.split(";")) > 1):
            return self._offline_process(text)

        # Check LLM provider availability
        self.llm_engine._resolve()
        client = self.llm_engine._client

        # If completely offline, fall back to rule-based execution
        if client is None or self.llm_engine._resolved_provider == "offline":
            return self._offline_process(text)

        # Assemble live system telemetry and personal intelligence context
        live_telemetry = get_live_system_context()
        personal_context = self.personal_intelligence.build_system_context()
        system_content = (
            f"{COGNITIVE_SYSTEM_PROMPT}\n\n"
            f"{personal_context}\n\n"
            f"[Live Real-Time Telemetry & Context]\n"
            f"{live_telemetry}\n"
        )

        # Build message history
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_content}]
        for turn in self.memory._turns:
            messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": text})

        executed_tools: list[ToolExecutionRecord] = []
        preferred_model = self.llm_engine._resolved_model or "gemini-flash-lite-latest"
        model_candidates = [
            preferred_model,
            "gemini-flash-lite-latest",
            "gemini-2.5-flash",
            "gemini-3-flash-preview",
            "gemini-flash-latest",
        ]
        unique_candidates: list[str] = []
        for c in model_candidates:
            if c not in unique_candidates:
                unique_candidates.append(c)

        # ReAct autonomous tool-calling loop
        for iteration in range(max_tool_iterations):
            response = None
            last_exc = None
            for cand in unique_candidates:
                try:
                    response = client.chat.completions.create(
                        model=cand,
                        messages=messages,
                        tools=AGENT_TOOLS,
                        temperature=0.4,
                        max_tokens=self.llm_engine.max_tokens or 600,
                    )
                    self.llm_engine._resolved_model = cand
                    break
                except Exception as exc:
                    last_exc = exc
                    logger.warning("Model %s failed: %s; trying next candidate", cand, exc)
                    continue

            if response is None:
                logger.error("All candidate LLM models failed: %s", last_exc)
                return self._offline_process(text)

            msg = response.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None)

            # If model didn't call any tools, we have our final response!
            if not tool_calls:
                final_content = msg.content or "Task completed, sir."
                self.memory.add("user", text)
                self.memory.add("assistant", final_content)
                return AgentTurnResult(
                    reply=final_content,
                    action="agent_conversation" if not executed_tools else "task_executed",
                    tools_executed=executed_tools,
                    success=True,
                )

            # Otherwise, execute each tool call
            # Add assistant message with tool_calls and thought signatures directly
            messages.append(msg)

            for tc in tool_calls:
                fn_name = tc.function.name
                raw_args = tc.function.arguments or "{}"
                try:
                    fn_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    fn_args = {}

                t_start = time.perf_counter()
                out_data, ok = self.execute_tool(fn_name, fn_args)
                duration_ms = (time.perf_counter() - t_start) * 1000

                executed_tools.append(
                    ToolExecutionRecord(
                        name=fn_name,
                        args=fn_args,
                        output=out_data,
                        success=ok,
                        duration_ms=duration_ms,
                    )
                )

                # Log tool execution to WAL
                if self.event_log:
                    self.event_log.audit(
                        stream_id="agent",
                        event_type="agent.tool_executed",
                        principal_id="cognitive_agent",
                        payload={
                            "tool": fn_name,
                            "args": fn_args,
                            "success": ok,
                            "duration_ms": duration_ms,
                        },
                    )

                # Append tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(out_data, default=str),
                })

        # If reached max iterations, ask model for final synthesis
        summary_model = self.llm_engine._resolved_model or preferred_model
        try:
            summary_resp = client.chat.completions.create(
                model=summary_model,
                messages=messages,
                temperature=0.5,
                max_tokens=400,
            )
            final_text = summary_resp.choices[0].message.content or "Completed actions, sir."
        except Exception as exc:
            # Do NOT report success here. This path previously raised NameError
            # on an undefined `model_name`, so the handler always ran and always
            # claimed the actions had succeeded. Report the failure instead.
            logger.warning("Final synthesis failed on model %s: %s", summary_model, exc)
            if executed_tools:
                done = sum(1 for t in executed_tools if t.success)
                failed = len(executed_tools) - done
                final_text = (
                    f"Ran {len(executed_tools)} action(s): {done} succeeded, "
                    f"{failed} failed. I could not summarize the results "
                    f"(synthesis on {summary_model} failed: {exc})."
                )
            else:
                final_text = f"No actions were run, and synthesis failed: {exc}."

        self.memory.add("user", text)
        self.memory.add("assistant", final_text)

        return AgentTurnResult(
            reply=final_text,
            action="task_executed",
            tools_executed=executed_tools,
            success=True,
        )

    def _offline_process(self, text: str) -> AgentTurnResult:
        """Deterministic offline fallback when no LLM API is available."""
        lowered = text.lower()

        # Multi-Step Task Autonomy (Sequential Decomposition & Execution)
        if " and then " in lowered or " then " in lowered or (";" in text and len(text.split(";")) > 1):
            delimiters = [" and then ", " then ", ";"]
            clauses = [text]
            for delim in delimiters:
                if delim in clauses[0].lower():
                    clauses = [c.strip() for c in re.split(re.escape(delim), text, flags=re.IGNORECASE) if c.strip()]
                    break

            if len(clauses) > 1:
                step_records: list[ToolExecutionRecord] = []
                step_replies: list[str] = []
                all_ok = True
                for i, clause in enumerate(clauses, 1):
                    sub_res = self._offline_process(clause)
                    if sub_res.tools_executed:
                        step_records.extend(sub_res.tools_executed)
                    step_replies.append(f"Step {i}: {sub_res.reply}")
                    if not sub_res.success:
                        all_ok = False
                        break
                return AgentTurnResult(
                    reply="\n".join(step_replies),
                    action="multi_step_executed",
                    tools_executed=step_records,
                    success=all_ok,
                )

        # Identity & Creator Profile Queries
        if any(w in lowered for w in ["who am i", "what is my name", "do you know me", "my profile", "who created you", "what do you know about me", "tell me about myself", "my active projects"]):
            p = self.personal_intelligence.profile
            projects_str = ", ".join(p.active_projects)
            reply = (
                f"You are {p.name}, my Creator and Chief Architect, sir. "
                f"You are operating from {p.location} ({p.timezone}). "
                f"Active endeavors include: {projects_str}. "
                f"My personal intelligence database retains {len(p.facts)} biographical facts and preferences regarding your workflow."
            )
            return AgentTurnResult(
                reply=reply,
                action="creator_profile_recalled",
                success=True,
            )

        if any(w in lowered for w in ["who are you", "what are you", "what is your name", "introduce yourself"]):
            reply = (
                "I am J.A.R.V.I.S., sir: Just A Rather Very Intelligent System. "
                "I serve as your autonomous spatial desktop companion and cognitive OS, "
                "equipped with over 2,400 specialized skills and direct workstation agency."
            )
            return AgentTurnResult(
                reply=reply,
                action="identify",
                success=True,
            )

        # Authentic British Persona Greetings
        if lowered in ["hello", "hi", "hey", "hey jarvis", "hello jarvis", "good morning", "good afternoon", "good evening", "greetings"]:
            return AgentTurnResult(
                reply=self.personal_intelligence.get_greeting(),
                action="greeting",
                success=True,
            )

        # Hardware Volume
        if any(w in lowered for w in ["volume up", "increase volume", "louder"]):
            self.execute_tool("system_control", {"action": "volume_up"})
            reply = self.personal_intelligence.enrich_response("volume_up", "Volume increased, sir.")
            return AgentTurnResult(reply=reply, action="volume_up")

        if any(w in lowered for w in ["volume down", "decrease volume", "softer"]):
            self.execute_tool("system_control", {"action": "volume_down"})
            reply = self.personal_intelligence.enrich_response("volume_down", "Volume decreased, sir.")
            return AgentTurnResult(reply=reply, action="volume_down")

        if any(w in lowered for w in ["mute", "silence"]):
            self.execute_tool("system_control", {"action": "mute_toggle"})
            reply = self.personal_intelligence.enrich_response("mute_toggle", "Audio mute toggled, sir.")
            return AgentTurnResult(reply=reply, action="mute_toggle")

        if any(w in lowered for w in ["lock pc", "lock screen", "lock workstation"]):
            self.execute_tool("system_control", {"action": "lock_workstation"})
            reply = self.personal_intelligence.enrich_response("lock_workstation", "Workstation locked and secured, sir.")
            return AgentTurnResult(reply=reply, action="lock_workstation")

        # Direct System Command / CMD Execution Prefix
        for prefix in ("cmd:", "run:", "powershell:", "ps:", "exec:"):
            if lowered.startswith(prefix):
                cmd_to_run = text[len(prefix):].strip()
                shell_val = "cmd" if prefix == "cmd:" else ("powershell" if prefix in ("powershell:", "ps:") else "auto")
                t_start = time.perf_counter()
                out_data, ok = self.execute_tool("run_system_command", {"command": cmd_to_run, "shell": shell_val})
                dur = (time.perf_counter() - t_start) * 1000
                stdout = out_data.get("stdout", "") if isinstance(out_data, dict) else str(out_data)
                stderr = out_data.get("stderr", "") if isinstance(out_data, dict) else ""
                reply = stdout or stderr or "Command executed with no output, sir."
                return AgentTurnResult(
                    reply=reply,
                    action="system_command",
                    tools_executed=[
                        ToolExecutionRecord(
                            name="run_system_command",
                            args={"command": cmd_to_run},
                            output=out_data,
                            success=ok,
                            duration_ms=dur,
                        )
                    ],
                    success=ok,
                )

        # Direct Adaptive Skill Learning Prefix
        for prefix in ("learn:", "teach:", "skill:"):
            if lowered.startswith(prefix):
                raw_payload = text[len(prefix):].strip()
                parts = [p.strip() for p in raw_payload.split("|")]
                skill_name = parts[0]
                code = parts[1] if len(parts) > 1 else "Write-Output 'Executing custom skill'"
                desc = parts[2] if len(parts) > 2 else f"Custom user skill for {skill_name}"
                t_start = time.perf_counter()
                out_data, ok = self.execute_tool(
                    "learn_skill",
                    {"skill_name": skill_name, "code": code, "description": desc},
                )
                dur = (time.perf_counter() - t_start) * 1000
                if ok:
                    # ADR-011 S2: learning writes a file; it does not grant
                    # execution. Say so plainly, or the reply implies the skill
                    # is now runnable when it is still blocked by S4.
                    reply = (
                        f"Skill '{skill_name}' learned and registered in the "
                        f"library, sir. It is not executable yet: "
                        f"review it, then run "
                        f"`jarvis skill admit {skill_name}` to allow execution."
                    )
                    action = "skill_learned"
                else:
                    # Never claim a learn succeeded when it did not.
                    detail = out_data.get("error", "learn_skill did not succeed")
                    reply = f"I did not learn '{skill_name}', sir. {detail}"
                    action = "skill_learn_failed"
                return AgentTurnResult(
                    reply=reply,
                    action=action,
                    tools_executed=[
                        ToolExecutionRecord(
                            name="learn_skill",
                            args={"skill_name": skill_name, "code": code, "description": desc},
                            output=out_data,
                            success=ok,
                            duration_ms=dur,
                        )
                    ],
                    success=ok,
                )

        # Direct Desktop Input / Mouse / Keyboard Emulation
        if lowered.startswith("mouse:"):
            cmd_body = text[6:].strip()
            parts = cmd_body.split()
            sub_act = parts[0].lower() if parts else "get_cursor_pos"
            t_start = time.perf_counter()
            if sub_act == "move" and len(parts) >= 3:
                out_data, ok = self.execute_tool("desktop_input", {"action": "move_mouse", "x": int(parts[1]), "y": int(parts[2])})
                reply = f"Mouse moved to ({parts[1]}, {parts[2]}), sir."
            elif sub_act in ("click", "double_click", "right_click"):
                x_val = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                y_val = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
                out_data, ok = self.execute_tool("desktop_input", {"action": sub_act, "x": x_val, "y": y_val})
                reply = f"Mouse {sub_act} executed, sir."
            elif sub_act == "scroll" and len(parts) >= 2:
                delta = int(parts[1])
                out_data, ok = self.execute_tool("desktop_input", {"action": "scroll", "scroll_delta": delta})
                reply = f"Mouse scrolled {delta} clicks, sir."
            else:
                out_data, ok = self.execute_tool("desktop_input", {"action": "get_cursor_pos"})
                reply = f"Current cursor position: ({out_data.get('x')}, {out_data.get('y')}), sir."

            dur = (time.perf_counter() - t_start) * 1000
            return AgentTurnResult(
                reply=reply,
                action="desktop_input",
                tools_executed=[ToolExecutionRecord(name="desktop_input", args={"command": cmd_body}, output=out_data, success=ok, duration_ms=dur)],
                success=ok,
            )

        if lowered.startswith("type:"):
            text_val = text[5:].strip()
            t_start = time.perf_counter()
            out_data, ok = self.execute_tool("desktop_input", {"action": "type_text", "text": text_val})
            dur = (time.perf_counter() - t_start) * 1000
            return AgentTurnResult(
                reply=f"Typed text: '{text_val}', sir.",
                action="desktop_input",
                tools_executed=[ToolExecutionRecord(name="desktop_input", args={"text": text_val}, output=out_data, success=ok, duration_ms=dur)],
                success=ok,
            )

        if lowered.startswith("key:"):
            key_val = text[4:].strip()
            t_start = time.perf_counter()
            out_data, ok = self.execute_tool("desktop_input", {"action": "press_key", "key": key_val})
            dur = (time.perf_counter() - t_start) * 1000
            return AgentTurnResult(
                reply=f"Key shortcut '{key_val}' pressed, sir.",
                action="desktop_input",
                tools_executed=[ToolExecutionRecord(name="desktop_input", args={"key": key_val}, output=out_data, success=ok, duration_ms=dur)],
                success=ok,
            )

        # Vision-Guided Desktop Perception & Control (No Coordinates Required)
        if any(w in lowered for w in ["inspect screen", "look at screen", "see screen", "what's on my screen", "screen status", "see windows"]):
            t_start = time.perf_counter()
            out_data, ok = self.execute_tool("screen_perception", {"action": "inspect_screen"})
            dur = (time.perf_counter() - t_start) * 1000
            active = out_data.get("active_window", "Desktop")
            wins = out_data.get("visible_windows", [])
            reply = f"Active window: '{active}'. Visible applications: {', '.join(wins[:5]) if wins else 'None'}."
            return AgentTurnResult(
                reply=reply,
                action="screen_perception",
                tools_executed=[ToolExecutionRecord(name="screen_perception", args={"action": "inspect_screen"}, output=out_data, success=ok, duration_ms=dur)],
                success=ok,
            )

        # Deterministic Filesystem File Writing (e.g. "Write a file named X with content Y in artifacts")
        file_write_match = re.search(
            r"(?:write|create)\s+(?:a\s+)?file\s+(?:named\s+)?['\"]?([a-zA-Z0-9_\-\.]+)['\"]?\s+(?:with\s+(?:the\s+)?content\s+)?['\"](.*?)['\"](?:\s+(?:in|into)\s+(?:the\s+)?(?:current\s+)?([a-zA-Z0-9_\-/\\\.]+)(?:\s+directory)?)?",
            text,
            re.IGNORECASE,
        )
        if file_write_match:
            filename = file_write_match.group(1).strip()
            content = file_write_match.group(2)
            directory = file_write_match.group(3) or "artifacts"
            target_path = Path(directory) / filename
            t_start = time.perf_counter()
            out_data, ok = self.execute_tool(
                "filesystem_operation",
                {"operation": "write_file", "path": str(target_path), "content": content},
            )
            dur = (time.perf_counter() - t_start) * 1000
            reply = f"File '{target_path.as_posix()}' written successfully with {len(content)} bytes, sir." if ok else f"Failed to write file '{target_path.as_posix()}': {out_data.get('error')}"
            return AgentTurnResult(
                reply=reply,
                action="filesystem_operation",
                tools_executed=[
                    ToolExecutionRecord(
                        name="filesystem_operation",
                        args={"operation": "write_file", "path": str(target_path), "content": content},
                        output=out_data,
                        success=ok,
                        duration_ms=dur,
                    )
                ],
                success=ok,
            )

        # Natural language GUI typing: "type <text> into <app>" or "input <text> into <app>"
        # Must explicitly NOT be a file operation, system command, or long sentence
        type_into_match = re.match(r"^(?:type|input)\s+['\"]?(.+?)['\"]?\s+(?:in|into)\s+([a-zA-Z0-9_\-\. ]{1,40})$", text, re.IGNORECASE)
        if type_into_match and not any(w in lowered for w in ["cmd:", "powershell:", "file", "directory", "folder", "artifacts"]):
            text_to_type = type_into_match.group(1).strip()
            target_app = type_into_match.group(2).strip()
            t_start = time.perf_counter()
            out_data, ok = self.execute_tool("screen_perception", {"action": "find_and_type", "target": target_app, "text": text_to_type})
            dur = (time.perf_counter() - t_start) * 1000
            if ok:
                reply = f"Focused '{out_data.get('target', target_app)}' and typed '{text_to_type}', sir."
            else:
                reply = f"Could not type into '{target_app}': {out_data.get('error', 'target not found')}, sir."
            return AgentTurnResult(
                reply=reply,
                action="screen_perception",
                tools_executed=[ToolExecutionRecord(name="screen_perception", args={"action": "find_and_type", "target": target_app, "text": text_to_type}, output=out_data, success=ok, duration_ms=dur)],
                success=ok,
            )

        # Natural language GUI clicking: "click <app/button>" or "focus <app>"
        click_match = re.match(r"^(?:click|focus|switch\s+to)\s+(?:on\s+)?([a-zA-Z0-9_\-\. ]{1,40})$", text, re.IGNORECASE)
        if click_match and not any(w in lowered for w in ["mouse:", "cmd:", "powershell:", "file", "and then", ";"]):
            target_app = click_match.group(1).strip()
            t_start = time.perf_counter()
            out_data, ok = self.execute_tool("screen_perception", {"action": "find_and_click", "target": target_app})
            dur = (time.perf_counter() - t_start) * 1000
            if ok:
                reply = f"Focused and activated '{out_data.get('target', target_app)}', sir."
            else:
                reply = f"Could not find target matching '{target_app}', sir."
            return AgentTurnResult(
                reply=reply,
                action="screen_perception",
                tools_executed=[ToolExecutionRecord(name="screen_perception", args={"action": "find_and_click", "target": target_app}, output=out_data, success=ok, duration_ms=dur)],
                success=ok,
            )

        # Skill Engine Direct Match
        ctx = SkillExecutionContext(workspace=Path.cwd() / "artifacts")
        res = self.skill_engine.execute_goal(text, ctx)
        if res.success and res.execution and res.execution.stdout:
            skill_name = res.selected_skill.title if res.selected_skill else "System Skill"
            return AgentTurnResult(
                reply=f"[{skill_name}]: {res.execution.stdout.strip()}",
                action="skill_executed",
            )

        # Dynamic fact learning fallback
        learn_note = self.personal_intelligence.process_user_turn_for_learning(text)
        if learn_note:
            return AgentTurnResult(
                reply=learn_note,
                action="personal_intelligence_learned",
                success=True,
            )

        return AgentTurnResult(
            reply=f"Acknowledged, sir: '{text}'. Core operational in offline mode.",
            action="offline_acknowledged",
        )
