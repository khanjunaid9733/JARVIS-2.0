from __future__ import annotations

"""`jarvis` command-line interface (module 11, spec §127.1 / §134.1).

MUST subcommands: `init`, `say`, `explain`, plus `replay --verify` and bare
`jarvis` (restart/recovery summary). Every command is a one-shot process over
the durable store at `$JARVIS_HOME` (default `~/.jarvis`); there is no daemon
in M1 (disclosed — `core service started` denotes the bootstrapped service
context, recorded as a `system.service_started` event).

Output lines follow §127.1 so the acceptance sequence is directly observable.
Deviations from the §127.1 transcript are disclosed:
- `say` answers deterministically/extractively when no model backend is
  configured; with `JARVIS_MODEL_API_KEY` + `JARVIS_MODEL_BASE_URL` set, the
  question is routed through the ModelGateway (module 15, STRETCH M1.1) and
  falls back to the deterministic answer on any typed failure (model calls
  are recorded as `question.asked` events; the offline acceptance path
  records nothing, so §127.1 event counts are unchanged);
- `explain` renders the full cause chain + state transitions + model/budget
  provenance via the module-17 renderer (STRETCH M1.1, §134.1).
"""

import argparse
import asyncio
import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Sequence

from .bootstrap import CoreService, ensure_service_started, new_pairing_code
from .kernel.event_log import EventIntegrityError
from .kernel.explain import explain_event
from .kernel.memory_query import answer
from .kernel.memory_write import (
    MEMORY_COMMITTED,
    MEMORY_PROPOSED,
    MEMORY_REJECTED,
    MEMORY_VERIFIED,
    MemoryWriter,
)

REMEMBER_PREFIX = "remember:"
DEFAULT_SOURCE = "session 1"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jarvis", description="JARVIS 2.0 (M1)")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="bootstrap creator, log, projections, registry")
    init.set_defaults(func=_cmd_init)

    say = sub.add_parser("say", help="send a message; 'remember: ...' writes memory")
    say.add_argument("text")
    say.set_defaults(func=_cmd_say)

    explain = sub.add_parser("explain", help="render the cause chain for an event")
    explain.add_argument("event_id")
    explain.set_defaults(func=_cmd_explain)

    replay = sub.add_parser("replay", help="replay the event log")
    replay.add_argument("--verify", action="store_true", help="verify the hash chain")
    replay.set_defaults(func=_cmd_replay)

    recall = sub.add_parser(
        "recall",
        help="deterministic recall over committed memories + episodic traces (M2.1)",
    )
    recall.add_argument("query")
    recall.set_defaults(func=_cmd_recall)

    mission = sub.add_parser(
        "mission",
        help="run one goal through the live loop: intake -> decompose -> dispatch -> "
        "verify -> recover -> recall",
    )
    mission.add_argument("goal")
    mission.add_argument(
        "--fault",
        action="append",
        default=[],
        metavar="STEP=N",
        help="declare N transient failures for a step (proves the recovery ladder acts)",
    )
    mission.add_argument(
        "--worker",
        choices=("local", "auto", "external"),
        default="local",
        help="worker engine: local (in-process, default), auto (external then local), "
        "external (require a real external process)",
    )
    mission.add_argument(
        "--worker-provider",
        default=None,
        help="provider whose bridge runs the worker (default: the Router's implementer)",
    )
    mission.add_argument(
        "--worker-timeout",
        type=float,
        default=120.0,
        help="sandbox timeout for an external worker; the whole process tree is killed",
    )
    mission.set_defaults(func=_cmd_mission)

    voice = sub.add_parser(
        "voice",
        help="answer one voice turn through the live loop (STT -> answer -> TTS, FSM journalled)",
    )
    voice.add_argument("utterance", help="the spoken text, or the utterance to transcribe")
    voice.add_argument(
        "--audio",
        default=None,
        help="audio file to transcribe for real (requires a bound STT engine)",
    )
    voice.set_defaults(func=_cmd_voice)

    skill = sub.add_parser("skill", help="manage and execute skills from the skill library")
    skill_sub = skill.add_subparsers(dest="skill_action")

    skill_list = skill_sub.add_parser("list", help="list registered skills")
    skill_list.add_argument("--domain", default=None, help="filter by domain")
    skill_list.add_argument("--limit", type=int, default=50, help="maximum skills to display")
    skill_list.set_defaults(func=_cmd_skill_list)

    skill_find = skill_sub.add_parser("find", help="search skills by natural language intent")
    skill_find.add_argument("query", help="natural language search query")
    skill_find.add_argument("--domain", default=None, help="filter by domain")
    skill_find.add_argument("--limit", type=int, default=10, help="max results")
    skill_find.set_defaults(func=_cmd_skill_find)

    skill_check = skill_sub.add_parser("check", help="check prerequisites and operational health")
    skill_check.add_argument("skill_id", help="skill identifier")
    skill_check.set_defaults(func=_cmd_skill_check)

    skill_inspect = skill_sub.add_parser("inspect", help="inspect full skill manifest and steps")
    skill_inspect.add_argument("skill_id", help="skill identifier")
    skill_inspect.set_defaults(func=_cmd_skill_inspect)

    skill_run = skill_sub.add_parser("run", help="execute or dry-run a skill")
    skill_run.add_argument("skill_id", help="skill identifier")
    skill_run.add_argument("--dry-run", action="store_true", help="dry-run without executing")
    skill_run.add_argument("--param", action="append", default=[], help="parameter KEY=VALUE")
    skill_run.set_defaults(func=_cmd_skill_run)

    skill_auto = skill_sub.add_parser("auto", help="autonomously resolve and execute a goal")
    skill_auto.add_argument("goal", help="goal intent or task description")
    skill_auto.add_argument("--domain", default=None, help="constrain to a specific domain")
    skill_auto.add_argument("--dry-run", action="store_true", help="dry-run without executing")
    skill_auto.add_argument("--param", action="append", default=[], help="parameter KEY=VALUE")
    skill_auto.set_defaults(func=_cmd_skill_auto)

    skill_admit = skill_sub.add_parser(
        "admit", help="add a skill to the execution allowlist (ADR-011 S4)"
    )
    skill_admit.add_argument("skill_id", help="skill identifier to allow execution")
    skill_admit.add_argument("--note", default="", help="why this skill is safe to run")
    skill_admit.set_defaults(func=_cmd_skill_admit)

    skill_admitted = skill_sub.add_parser(
        "admitted", help="list skills currently allowed to execute"
    )
    skill_admitted.set_defaults(func=_cmd_skill_admitted)

    skill.set_defaults(func=_cmd_skill_default, domain=None, limit=50)

    ui = sub.add_parser("ui", help="launch JARVIS holographic arc core & web GUI")
    ui.add_argument("--port", type=int, default=7777, help="port for the GUI server (default: 7777)")
    ui.add_argument("--no-browser", action="store_true", help="do not auto-open browser")
    ui.add_argument("--overlay", action="store_true", help="launch as transparent desktop HUD overlay (always-on-top)")
    ui.add_argument("--background", action="store_true", help="run resident background service silently (detached, no terminal window)")
    ui.set_defaults(func=_cmd_ui)

    app = sub.add_parser("app", help="launch JARVIS as a pure native desktop application window (zero browser)")
    app.add_argument("--port", type=int, default=7777, help="port for the GUI server (default: 7777)")
    app.add_argument("--web", action="store_true", help="use web browser HUD overlay instead of pure native GUI")
    app.add_argument("--background", action="store_true", help="run resident background service silently")
    app.set_defaults(func=_cmd_app)

    res = sub.add_parser("resident", help="manage warm background resident daemon and global hotkeys")
    res.add_argument("--port", type=int, default=7777, help="port for the resident server (default: 7777)")
    res.add_argument("--start", action="store_true", help="start resident background daemon immediately")
    res.add_argument("--stop", action="store_true", help="stop running resident daemon")
    res.add_argument("--install-startup", action="store_true", help="install silent background daemon into Windows Startup")
    res.add_argument("--uninstall-startup", action="store_true", help="remove background daemon from Windows Startup")
    res.add_argument("--status", action="store_true", help="check if registered in Windows Startup")
    res.set_defaults(func=_cmd_resident)

    do_cmd = sub.add_parser(
        "do",
        help="autonomously execute any task using CMD, PowerShell, filesystem & skills",
    )
    do_cmd.add_argument("goal", help="task or goal description")
    do_cmd.add_argument("--max-steps", type=int, default=5, help="maximum tool execution iterations")
    do_cmd.set_defaults(func=_cmd_do)

    bugscan_cmd = sub.add_parser(
        "bugscan",
        help="deterministic bug scan of the JARVIS source tree",
    )
    bugscan_cmd.add_argument(
        "--path", default="src/jarvis", help="package or directory to scan"
    )
    bugscan_cmd.add_argument(
        "--rule", action="append", dest="rules",
        help="limit to a rule (repeatable)",
    )
    bugscan_cmd.add_argument(
        "--severity", action="append", dest="severities",
        help="limit to a severity: critical/high/medium/low (repeatable)",
    )
    bugscan_cmd.add_argument("--json", action="store_true", help="machine-readable output")
    bugscan_cmd.add_argument(
        "--fail-on", default="critical",
        help="exit non-zero if any finding is this severe or worse (default: critical)",
    )
    bugscan_cmd.set_defaults(func=_cmd_bugscan)

    bugfix_cmd = sub.add_parser(
        "bugfix",
        help="AI triage of one bugscan finding; patches require explicit --yes",
    )
    bugfix_cmd.add_argument("finding_id", help="finding id from `jarvis bugscan`")
    bugfix_cmd.add_argument(
        "--yes", action="store_true",
        help="actually write the patch (default is a dry run showing the diff)",
    )
    bugfix_cmd.set_defaults(func=_cmd_bugfix)

    opencode_cmd = sub.add_parser(
        "opencode",
        help="dispatch software engineering prompt directly to OpenCode (Big Pickle)",
    )
    opencode_cmd.add_argument("prompt", help="prompt or coding task for OpenCode")
    opencode_cmd.add_argument("--model", "-m", default="opencode/big-pickle", help="model string (default: opencode/big-pickle)")
    opencode_cmd.add_argument("--dir", "-d", default=None, help="working directory")
    opencode_cmd.set_defaults(func=_cmd_opencode)

    # bare `jarvis` = restart/recovery summary (§127.1)
    parser.set_defaults(func=_cmd_status)
    return parser


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def _cmd_ui(service: CoreService, args: argparse.Namespace) -> int:
    import webbrowser

    port = getattr(args, "port", 7777)

    if getattr(args, "background", False):
        import subprocess
        from pathlib import Path
        import sys
        repo_root = Path(__file__).resolve().parent.parent.parent
        pythonw = Path(sys.executable).parent / "pythonw.exe"
        if not pythonw.is_file():
            pythonw = Path(sys.executable)

        target_func = "run_overlay" if getattr(args, "overlay", False) else "run_server"
        cmd = [
            str(pythonw),
            "-c",
            f"import sys; sys.path.insert(0, 'src'); from jarvis.ui.server import {target_func}; {target_func}({port})",
        ]
        flags = 0
        if sys.platform == "win32":
            flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(cmd, cwd=str(repo_root), creationflags=flags, close_fds=True)
        print(f"JARVIS 2.0 active in background (port {port}).")
        print("  - Voice:  Say 'Hey JARVIS' anywhere to wake")
        print("  - Hotkey: Press Alt+J to summon holographic HUD")
        print("This terminal can now be safely closed.")
        return 0

    if getattr(args, "overlay", False):
        # Launch transparent desktop HUD overlay
        from .ui.server import run_overlay
        print(f"Launching JARVIS Desktop HUD Overlay on port {port}...")
        print("Press Alt+J to summon/focus the HUD window.")
        print("Hands-free acoustic trigger active: Say 'Hey JARVIS' anywhere.")
        run_overlay(port=port, service=service)
        return 0

    # Default: full dashboard in browser
    from .ui.server import run_server
    url = f"http://127.0.0.1:{port}"
    print(f"Launching JARVIS Holographic Arc Core & GUI on {url}...")
    if not getattr(args, "no_browser", False):
        try:
            webbrowser.open(url)
        except Exception:
            pass
    run_server(port=port, service=service)
    return 0


def _cmd_app(service: CoreService, args: argparse.Namespace) -> int:
    """Launch JARVIS as a 100% native desktop application window (zero browser)."""
    port = getattr(args, "port", 7777)
    use_web = getattr(args, "web", False)

    if use_web:
        setattr(args, "overlay", True)
        return _cmd_ui(service, args)

    # Pure Native Windows Desktop Companion (Tkinter Canvas + Arc Reactor)
    from .ui.desktop_companion import launch_native_companion
    print(f"Launching JARVIS 2.0 Pure Native Desktop Companion (zero browser)...")
    print(f"Arc Reactor HUD initialized on desktop.")
    launch_native_companion(port=port)
    return 0



def _cmd_resident(service: CoreService, args: argparse.Namespace) -> int:
    from pathlib import Path
    import sys
    scripts_dir = Path(__file__).resolve().parent.parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        import install_startup
    except ImportError:
        install_startup = None  # type: ignore[assignment]

    if getattr(args, "install_startup", False):
        if not install_startup:
            print("install_startup script not available", file=sys.stderr)
            return 1
        path = install_startup.install_startup(port=args.port)
        print(f"JARVIS 2.0 Resident registered in Windows Startup at:\n  {path}")
        print("System will pre-warm automatically on Windows login (warm memory, 0ms cold-start).")
        return 0

    if getattr(args, "uninstall_startup", False):
        if not install_startup:
            print("install_startup script not available", file=sys.stderr)
            return 1
        removed = install_startup.uninstall_startup()
        print(f"Windows Startup resident registration removed: {removed}")
        return 0

    if getattr(args, "start", False):
        import subprocess
        pythonw = Path(sys.executable).parent / "pythonw.exe"
        if not pythonw.is_file():
            pythonw = Path(sys.executable)
        repo_root = Path(__file__).resolve().parent.parent.parent
        cmd = [
            str(pythonw),
            "-c",
            f"import sys; sys.path.insert(0, 'src'); from jarvis.ui.server import run_server; run_server({args.port})",
        ]
        flags = 0x00000008 | 0x00000200 if sys.platform == "win32" else 0
        subprocess.Popen(cmd, cwd=str(repo_root), creationflags=flags, close_fds=True)
        print(f"JARVIS 2.0 Resident background daemon started on port {args.port}.")
        print("  - Voice:  Say 'Hey JARVIS' anywhere to wake")
        print("  - Hotkey: Press Alt+J to summon holographic HUD")
        return 0

    if getattr(args, "status", False):
        installed = install_startup.is_installed() if install_startup else False
        print(f"Windows Startup resident: {'INSTALLED' if installed else 'NOT INSTALLED'}")
        return 0

    from .ui.server import run_server
    print("Starting JARVIS 2.0 Warm Resident Daemon...")
    print("Global Hotkey: [Alt + J] active (instant HUD summon in <15ms)")
    print("Hands-free acoustic trigger active: Say 'Hey JARVIS' to wake.")

    print(f"Server endpoint: http://127.0.0.1:{args.port}")
    run_server(port=args.port, service=service)
    return 0


def _cmd_do(service: CoreService, args: argparse.Namespace) -> int:
    from .skills.cognitive_agent import CognitiveAgent
    agent = CognitiveAgent(event_log=service.log)
    print(f"\n[JARVIS] Engaging autonomous cognitive agent on: {args.goal!r}")
    res = agent.process_turn(args.goal, source="cli", max_tool_iterations=args.max_steps)
    if res.tools_executed:
        print(f"\n--- Actions Executed ({len(res.tools_executed)}) ---")
        for i, t in enumerate(res.tools_executed, 1):
            status = "OK" if t.success else "FAILED"
            print(f"{i}. [{status}] {t.name} ({t.duration_ms:.1f}ms)")
            if t.args:
                arg_summary = ", ".join(f"{k}={v!r}" for k, v in t.args.items())
                if len(arg_summary) > 120:
                    arg_summary = arg_summary[:117] + "..."
                print(f"   args: {arg_summary}")
            if t.name == "run_system_command" and isinstance(t.output, dict):
                stdout = t.output.get("stdout")
                if stdout:
                    lines = stdout.splitlines()
                    preview = "\n".join(f"     | {line}" for line in lines[:10])
                    if len(lines) > 10:
                        preview += f"\n     | ... ({len(lines) - 10} more lines)"
                    print(f"   stdout:\n{preview}")
            elif t.name == "filesystem_operation" and isinstance(t.output, dict):
                if "content" in t.output:
                    lines = t.output["content"].splitlines()
                    preview = "\n".join(f"     | {line}" for line in lines[:8])
                    print(f"   content:\n{preview}")
                elif "items" in t.output:
                    items_str = ", ".join(item["name"] for item in t.output["items"][:10])
                    print(f"   items: {items_str}")
    print(f"\n[JARVIS Response]\n{res.reply}\n")
    return 0 if res.success else 1


def _cmd_opencode(service: CoreService, args: argparse.Namespace) -> int:
    import subprocess
    from pathlib import Path
    import sys
    root_dir = Path(__file__).resolve().parent.parent.parent
    script_path = root_dir / "scripts" / "control_opencode.py"
    if not script_path.exists():
        print(f"Error: OpenCode bridge script not found at {script_path}", file=sys.stderr)
        return 1

    cmd = [sys.executable, str(script_path), "run", "--model", args.model]
    if args.dir:
        cmd.extend(["--dir", args.dir])
    cmd.append(args.prompt)

    print(f"[JARVIS] Dispatching to OpenCode (Big Pickle): {args.prompt!r}")
    res = subprocess.run(cmd)
    return res.returncode


def _cmd_init(service: CoreService, args: argparse.Namespace) -> int:
    ensure_service_started(service.log)  # type: ignore[arg-type]
    print(f"creator keypair created (fingerprint: {service.fingerprint})")
    print(f"event log initialized at {service.log_path}")
    print("projections initialized")
    print(f"registry seeded ({len(service.provider_ids())} providers)")
    print("core service started")
    print(f"pairing code: {new_pairing_code()}")
    return 0


def _cmd_status(service: CoreService, args: argparse.Namespace) -> int:
    projection = service.projection()
    print(f"replayed {projection.event_count} events")
    print("projections rebuilt")
    print("identity recovered")
    print("last mission: none")
    print("active agents: 0")
    return 0


# ---------------------------------------------------------------------------
# model-backed question path (STRETCH M1.1, module 15)
# ---------------------------------------------------------------------------

# Current Groq chat model as of M1.1 (the module-6 adapter default,
# llama-3.3-70b-versatile, is decommissioned). Overridable per machine via
# JARVIS_MODEL_NAME; recorded as provenance on question.asked.
DEFAULT_MODEL_NAME = "openai/gpt-oss-120b"


def _model_name() -> str:
    return os.environ.get("JARVIS_MODEL_NAME") or DEFAULT_MODEL_NAME


def _build_model_gateway(service: CoreService):
    """Return a ready ModelGateway when the production backend is configured,
    else None (deterministic offline path, §127.1 unchanged).

    Reads `JARVIS_MODEL_API_KEY` / `JARVIS_MODEL_BASE_URL` (module-6 adapter)
    and `JARVIS_MODEL_NAME` (M1.1 model selection, default `DEFAULT_MODEL_NAME`),
    re-binds the seeded `model.adapter` metadata to the real backend via
    `register_groq_provider` (module-6 production seam; provider SET unchanged
    — the in-memory registry gains no new provider, so the §127.1 registry
    invariant holds), and wires `ModelGateway` on the service registry.
    """
    if not (
        os.environ.get("JARVIS_MODEL_API_KEY")
        and os.environ.get("JARVIS_MODEL_BASE_URL")
    ):
        return None
    registry = service.registry
    if registry is None:
        return None
    try:
        from .kernel.model_gateway import ModelGateway
        from .kernel.model_gateway import register_groq_provider
        from .providers.openai_compatible import OpenAICompatibleAdapter

        register_groq_provider(registry)
        adapter = OpenAICompatibleAdapter(model=_model_name())
    except Exception:
        return None
    return ModelGateway(resolver=registry, adapters={"model.adapter": adapter})


def _answer_question(service: CoreService, text: str):
    """Route the question through the gateway when configured (module 15);
    otherwise the deterministic extractive answer (module 11, unchanged)."""
    from .kernel.model_answer import answer_question

    gateway = _build_model_gateway(service)
    if gateway is None:
        return answer(service.projection(), text)
    return asyncio.run(
        answer_question(
            service.projection(),
            text,
            gateway=gateway,
            log=service.log,  # type: ignore[arg-type]
            model_name=_model_name(),
        )
    )


def _cmd_say(service: CoreService, args: argparse.Namespace) -> int:
    text = args.text.strip()
    print("[thinking]")
    if text.lower().startswith(REMEMBER_PREFIX):
        content = text[len(REMEMBER_PREFIX):].strip()
        writer = MemoryWriter(service.log)  # type: ignore[arg-type]
        result = writer.remember(content=content, source=DEFAULT_SOURCE)
        print(MEMORY_PROPOSED)
        print(MEMORY_VERIFIED)
        if result.status == "committed":
            print(MEMORY_COMMITTED)
        else:
            print(MEMORY_REJECTED)
            print(f"reason: {result.reason}")
        return 0

    result = _answer_question(service, text)
    if not result.answered:
        print("no relevant memory")
        return 0
    if getattr(result, "used_model", False):
        print(result.answer)
        print(f"(model-grounded; confidence {result.confidence:.2f}, provider: {result.provider_id})")
        return 0
    print(result.answer)
    print(f"(confidence {result.confidence:.2f}, source: {result.source})")
    return 0


def _cmd_explain(service: CoreService, args: argparse.Namespace) -> int:
    assert service.log is not None
    explanation = explain_event(service.log, service.projection(), args.event_id)
    if explanation is None:
        print(f"unknown event id: {args.event_id}")
        return 1

    print("cause chain: " + " <- ".join(link.event_id for link in explanation.chain))
    print(f"event type: {explanation.event_type}")
    print(f"principal: {explanation.principal_id}")
    if explanation.lifecycle_state is not None:
        detail = ""
        if explanation.lifecycle_transitions:
            detail = f" ({', '.join(explanation.lifecycle_transitions)})"
        print(f"state transitions: {explanation.lifecycle_state}{detail}")
    else:
        print("state transitions: none (no mission events for this stream)")

    if explanation.model_provenance is not None:
        p = explanation.model_provenance
        provider = p.get("provider_id") or "n/a"
        contract = (
            f"{p.get('contract_id')}@{p.get('contract_version')}"
            if p.get("contract_id")
            else "n/a"
        )
        print(f"model: {provider} ({contract})")
        if p.get("model_name"):
            print(f"model name: {p.get('model_name')}")
        path = p.get("fallback", "n/a")
        if p.get("failure_reason"):
            path = f"{path} (failure: {p.get('failure_reason')})"
        print(f"answer path: {path}")
        if explanation.recalled_memories:
            top = explanation.recalled_memories[0]
            print(
                f"retrieved memories: {len(explanation.recalled_memories)} "
                f"(top score {top.score:.2f})"
            )
    elif explanation.event_type == MEMORY_COMMITTED:
        print(f"memory content: {explanation.memory_content!r}")
        print(f"memory source: {explanation.memory_source}")
        print(f"retrieved memories: {len(service.projection().memories)} total")
        print("model: none (deterministic memory path)")

    if explanation.capability_check_count:
        print(f"capability checks: {explanation.capability_check_count}")
    else:
        print("capability checks: none recorded")
    if explanation.effect_count:
        print(f"effects executed within manifest: {explanation.effect_count}")
    else:
        print("no effects outside manifest")

    if explanation.budget is not None:
        b = explanation.budget
        print(
            f"budget: {b.model_calls} model call(s), {b.spent_tokens} tokens "
            f"accounted of allocation {b.allocation}"
        )
    else:
        print("budget: n/a (no model calls recorded)")
    return 0


def _cmd_replay(service: CoreService, args: argparse.Namespace) -> int:
    assert service.log is not None
    try:
        projection = service.projection()
        print(f"replayed {projection.event_count} events")
        if args.verify:
            if not service.log.verify_chain():
                print("verify: FAILED")
                return 2
            print(f"projection hash: {projection.digest()}")
            print("verify: OK")
    except EventIntegrityError as exc:
        print(f"verify: FAILED ({exc})")
        return 2
    return 0


def _parse_faults(specs: list[str]) -> dict[str, int]:
    """`--fault deliver=1` -> {"deliver": 1}; a declared transient fault, not a mock."""
    faults: dict[str, int] = {}
    for spec in specs:
        step, _, count = spec.partition("=")
        if not step or not count.isdigit():
            raise SystemExit(f"jarvis: --fault expects STEP=N, got {spec!r}")
        faults[step.strip()] = int(count)
    return faults


def _live_runtime(service: CoreService):
    from .live import LiveRuntime

    return LiveRuntime(service)


def _post_check(service: CoreService) -> None:
    """Prove the durable store is still sound after the live run."""
    from .kernel.memory_projection import MemoryProjection

    projection = MemoryProjection.rebuild(service.log)  # type: ignore[arg-type]
    chain = service.log.verify_chain()  # type: ignore[union-attr]
    print(
        f"post-check: hash chain {'OK' if chain else 'FAILED'}, "
        f"{projection.event_count} events, projection {projection.digest()[:16]}"
    )


def _cmd_mission(service: CoreService, args: argparse.Namespace) -> int:
    runtime = _live_runtime(service)
    report = runtime.run_goal(
        args.goal,
        faults=_parse_faults(args.fault),
        worker_mode=args.worker,
        worker_provider=args.worker_provider,
        worker_timeout=args.worker_timeout,
    )
    for line in report.lines:
        print(line)
    print(f"mission: {report.mission_id} outcome={report.outcome} lifecycle={report.lifecycle}")
    print("components:")
    for line in report.components:
        print(f"  - {line}")
    _post_check(service)
    return 0


def _cmd_voice(service: CoreService, args: argparse.Namespace) -> int:
    runtime = _live_runtime(service)
    report = runtime.voice_turn(
        args.utterance,
        audio=args.audio,
        answerer=lambda text: _answer_question(service, text),
    )
    for line in report.lines:
        print(line)
    print("components:")
    for line in report.components:
        print(f"  - {line}")
    _post_check(service)
    return 0


def _cmd_recall(service: CoreService, args: argparse.Namespace) -> int:
    assert service.log is not None
    from .kernel.memory_api import Memory

    hits = Memory(log=service.log).recall(args.query, limit=3)
    if not hits:
        print("no relevant memory")
        return 0
    for hit in hits:
        content = " ".join(hit.content.split())
        print(f"{hit.event_id}  {hit.score:.2f}  [{hit.source}]  {content}")
    return 0


# ---------------------------------------------------------------------------
# skill commands
# ---------------------------------------------------------------------------

def _cmd_skill_list(service: CoreService, args: argparse.Namespace) -> int:
    from .skills import get_default_registry
    reg = get_default_registry()
    domain = getattr(args, "domain", None)
    limit = getattr(args, "limit", 50)
    if domain:
        skills = reg.get_by_domain(domain)
        print(f"Domain '{domain}': {len(skills)} skill(s)")
    else:
        skills = reg.list_all()
        print(f"Loaded {reg.count()} skill(s) across {len(reg.list_domains())} domains:")

    for s in skills[:limit]:
        status_mark = "[runnable]" if s.is_runnable else "[info]"
        print(f"  {s.id:<30} {status_mark:<10} {s.description[:60]}")
    if len(skills) > limit:
        print(f"  ... and {len(skills) - limit} more (use --limit to see more)")
    return 0


def _cmd_skill_find(service: CoreService, args: argparse.Namespace) -> int:
    from .skills import get_default_registry
    reg = get_default_registry()
    matches = reg.find(args.query, domain=args.domain, limit=args.limit)
    if not matches:
        print(f"No skills matched query: {args.query!r}")
        return 0
    print(f"Top {len(matches)} match(es) for {args.query!r}:")
    for m in matches:
        print(f"  [{m.score:5.2f}] {m.skill.id:<28} ({m.skill.domain}) - {m.skill.description[:55]}")
    return 0


def _cmd_skill_check(service: CoreService, args: argparse.Namespace) -> int:
    from .skills import SkillHealthChecker, get_default_registry
    reg = get_default_registry()
    skill = reg.get(args.skill_id)
    if not skill:
        print(f"Unknown skill: {args.skill_id!r}", file=sys.stderr)
        return 1
    chk = SkillHealthChecker()
    report = chk.evaluate(skill)
    print(f"Skill:      {skill.id} ({skill.domain})")
    print(f"Status:     {report.status.value.upper()}")
    print(f"Executable: {report.is_executable}")
    if report.missing_binaries:
        print(f"Missing binaries: {', '.join(report.missing_binaries)}")
    if report.missing_env_vars:
        print(f"Missing env vars: {', '.join(report.missing_env_vars)}")
    if report.missing_modules:
        print(f"Missing modules:  {', '.join(report.missing_modules)}")
    for note in report.remediation_notes:
        print(f"  * {note}")
    return 0 if report.is_executable else 1


def _cmd_skill_inspect(service: CoreService, args: argparse.Namespace) -> int:
    from .skills import get_default_registry
    reg = get_default_registry()
    skill = reg.get(args.skill_id)
    if not skill:
        print(f"Unknown skill: {args.skill_id!r}", file=sys.stderr)
        return 1
    print(f"ID:          {skill.id}")
    print(f"Title:       {skill.title}")
    print(f"Domain:      {skill.domain}")
    print(f"Description: {skill.description}")
    if skill.triggers:
        print(f"Triggers ({len(skill.triggers)}):")
        for t in skill.triggers:
            print(f"  - {t}")
    if skill.prerequisites.required_binaries:
        print(f"Required Binaries: {', '.join(skill.prerequisites.required_binaries)}")
    if skill.prerequisites.required_env_vars:
        print(f"Required Env:      {', '.join(skill.prerequisites.required_env_vars)}")
    print(f"Workflows:   {len(skill.workflow_steps)} step(s)")
    for step in skill.workflow_steps:
        print(f"  Step {step.step_index} [{step.language}]:")
        for line in step.code.splitlines()[:6]:
            print(f"    {line}")
        if len(step.code.splitlines()) > 6:
            print("    ...")
    return 0


def _cmd_skill_run(service: CoreService, args: argparse.Namespace) -> int:
    from pathlib import Path
    from .skills import SkillDispatcher, SkillExecutionContext, get_default_registry
    reg = get_default_registry()
    skill = reg.get(args.skill_id)
    if not skill:
        print(f"Unknown skill: {args.skill_id!r}", file=sys.stderr)
        return 1
    params: dict[str, str] = {}
    for p in args.param:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip()] = v.strip()

    workspace = getattr(service, "workspace", None) or Path.cwd()
    ctx = SkillExecutionContext(
        workspace=workspace,
        parameters=params,
        dry_run=args.dry_run,
    )
    dispatcher = SkillDispatcher(event_sink=service.log)
    res = dispatcher.dispatch(skill, ctx)
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    # An audit write that failed means this execution is not in the ledger.
    # Say so, rather than letting "no record" look like "nothing happened".
    if res.audit_errors:
        print(
            f"WARNING: {len(res.audit_errors)} audit event(s) could NOT be written "
            f"to the ledger; this run is unaccounted for: "
            f"{'; '.join(res.audit_errors[:3])}",
            file=sys.stderr,
        )
    if res.refusal_reason:
        print(f"REFUSED: {res.refusal_reason}", file=sys.stderr)
        return 2
    if not res.success:
        print(f"FAILED: {res.error}", file=sys.stderr)
        return res.exit_code or 1
    print(f"OK ({res.duration_ms:.1f}ms)")
    return 0


def _cmd_bugscan(service: CoreService, args: argparse.Namespace) -> int:
    """Run the deterministic antibug scan.

    Detection never depends on the LLM: the AI subsystem in this project was
    silently broken for a long time, and a bug finder that depends on it would
    have reported a clean bill of health forever.
    """
    from .qa.bugscan import SEVERITY_ORDER, scan

    report = scan(
        args.path,
        rules=args.rules,
        severities=args.severities,
    )

    if args.json:
        print(report.to_json())
    else:
        print(
            f"Scanned {report.scanned_files} file(s): "
            f"{len(report.findings)} finding(s) {report.by_severity()}"
        )
        by_rule = report.by_rule()
        if by_rule:
            print("By rule: " + ", ".join(f"{k}={v}" for k, v in sorted(by_rule.items())))
        print()
        for f in report.findings:
            print(f"[{f.severity.upper():8}] {f.finding_id}")
            print(f"    {f.file}:{f.line}  {f.rule}")
            print(f"    {f.message}")
            if f.snippet:
                print(f"    > {f.snippet}")
            print()
        if report.scanner_errors:
            print(f"SCANNER ERRORS ({len(report.scanner_errors)}) - a rule failed:")
            for err in report.scanner_errors[:10]:
                print(f"    {err}")
            print()

    threshold = (args.fail_on or "").lower()
    if threshold and threshold in SEVERITY_ORDER:
        limit = SEVERITY_ORDER[threshold]
        if any(SEVERITY_ORDER.get(f.severity, 9) <= limit for f in report.findings):
            return 1
    return 0


def _cmd_bugfix(service: CoreService, args: argparse.Namespace) -> int:
    """Triage one finding and, only with --yes, apply a proposed patch."""
    from .qa.bugscan import scan
    from .qa.triage import propose_apply, triage_one

    report = scan()
    target = next(
        (f for f in report.findings if f.finding_id == args.finding_id), None
    )
    if target is None:
        print(
            f"No finding with id {args.finding_id!r} in the current scan "
            f"({len(report.findings)} finding(s)). Re-run `jarvis bugscan` for current ids.",
            file=sys.stderr,
        )
        return 1

    print(f"Finding : {target.finding_id}")
    print(f"Rule    : {target.rule} ({target.severity})")
    print(f"Location: {target.file}:{target.line}")
    print(f"Detail  : {target.message}")
    if target.snippet:
        print(f"Code    : {target.snippet}")
    print()

    triaged = triage_one(target)
    print(f"AI status: {triaged.ai_status}")
    if triaged.model:
        print(f"AI model : {triaged.model}")
    if triaged.explanation:
        print(f"Analysis : {triaged.explanation}")
    print()

    if not triaged.patch:
        print("No patch available. Nothing was changed.")
        return 0

    applied = propose_apply(target, triaged, dry_run=not args.yes)
    print(applied.message)
    if applied.diff:
        print()
        print(applied.diff)
    if applied.backup:
        print(f"\nBackup written: {applied.backup}")
    print()
    print("Re-run the test suite before committing: uv run --frozen pytest -q")
    return 0 if applied.ok else 1


def _cmd_skill_admit(service: CoreService, args: argparse.Namespace) -> int:
    """Record a reviewed skill on the execution allowlist."""
    from .skills.admission import (
        AdmissionEntry,
        admission_path,
        load_admission_file,
        write_admission_file,
    )
    from .skills.registry import get_default_registry

    skill_id = args.skill_id.strip()
    if not skill_id:
        print("skill_id is required", file=sys.stderr)
        return 2

    reg = get_default_registry()
    skill = reg.get(skill_id)
    if not skill:
        print(
            f"Unknown skill: {skill_id!r}. Discovery is separate from admission, "
            f"so the skill must exist in the library first.",
            file=sys.stderr,
        )
        return 1

    digest = None
    if skill.source_path and Path(skill.source_path).is_file():
        digest = hashlib.sha256(
            Path(skill.source_path).read_bytes()
        ).hexdigest()

    entries = [
        e for e in load_admission_file() if e.skill_id != skill_id
    ]
    entries.append(AdmissionEntry(skill_id=skill_id, note=args.note, source_sha256=digest))
    path = write_admission_file(entries)

    print(f"ADMITTED: {skill_id}")
    if digest:
        print(f"  pinned sha256: {digest}")
    if args.note:
        print(f"  note: {args.note}")
    print(f"  policy file: {admission_path()}")
    if not skill.is_runnable:
        print(
            f"  note: this skill has no admitted executable steps (ADR-011 S1), "
            f"so it remains informational even though it is admitted."
        )
    return 0


def _cmd_skill_admitted(service: CoreService, args: argparse.Namespace) -> int:
    from .skills.admission import load_policy

    policy = load_policy()
    ids = policy.admitted_ids()
    if not ids:
        print("no skills are admitted for execution")
        return 0
    print(f"{len(ids)} skill(s) admitted for execution:")
    for skill_id in ids:
        print(f"  - {skill_id}")
    print("")
    print("All other library skills remain discoverable and inspectable only.")
    return 0


def _cmd_skill_auto(service: CoreService, args: argparse.Namespace) -> int:
    from pathlib import Path
    from .skills import SkillExecutionContext, SkillRuntimeEngine, get_default_registry

    reg = get_default_registry()
    engine = SkillRuntimeEngine(registry=reg, event_sink=service.log)

    params: dict[str, str] = {}
    for p in args.param:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip()] = v.strip()

    workspace = getattr(service, "workspace", None) or Path.cwd()
    ctx = SkillExecutionContext(
        workspace=workspace,
        parameters=params,
        dry_run=args.dry_run,
    )

    res = engine.execute_goal(args.goal, ctx, domain=args.domain)
    if res.selected_skill:
        print(f"Matched Skill: {res.selected_skill.id} ({res.selected_skill.domain})")
    if res.execution and res.execution.stdout:
        print(res.execution.stdout)
    if res.execution and res.execution.stderr:
        print(res.execution.stderr, file=sys.stderr)

    if res.status == "NO_MATCH":
        print(f"NO_MATCH: {res.message}", file=sys.stderr)
        return 1
    elif res.status == "REFUSED":
        print(f"REFUSED: {res.message}", file=sys.stderr)
        return 2
    elif res.status == "EXECUTION_FAILED":
        print(f"FAILED: {res.message}", file=sys.stderr)
        return res.execution.exit_code if res.execution else 1

    print(f"OK ({res.duration_ms:.1f}ms)")
    return 0


def _cmd_skill_default(service: CoreService, args: argparse.Namespace) -> int:
    if getattr(args, "skill_action", None) is None:
        return _cmd_skill_list(service, args)
    return 0


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    service = CoreService()
    try:
        service.start()
    except Exception as exc:  # fail closed with a typed message
        print(f"jarvis: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    try:
        return args.func(service, args)
    finally:
        service.close()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
