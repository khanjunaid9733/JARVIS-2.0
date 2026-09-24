from __future__ import annotations

"""Autonomous OpenCode CLI & Daemon Controller (scripts/control_opencode.py).

Provides deterministic headless control over OpenCode (Big Pickle) from
Antigravity, JARVIS, or command-line scripts without TUI deadlocks or terminal hangs.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "google/gemini-3.1-flash-lite"
DEFAULT_PORT = 4096
DEFAULT_HOST = "127.0.0.1"


def get_opencode_cmd() -> str:
    """Find the runnable opencode command executable or shim."""
    resolved = shutil.which("opencode")
    if resolved:
        return resolved
    if sys.platform == "win32":
        npm_path = Path(os.environ.get("APPDATA", "")) / "npm" / "opencode.cmd"
        if npm_path.exists():
            return str(npm_path)
    raise FileNotFoundError("Could not find 'opencode' command on PATH.")


def is_server_alive(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    """Check if the headless OpenCode server is reachable and healthy."""
    url = f"http://{host}:{port}/session"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_server(
    host: str = DEFAULT_HOST, port: int = DEFAULT_PORT
) -> dict[str, Any]:
    """Start the headless OpenCode server as a background daemon if not already running."""
    if is_server_alive(host, port):
        return {"status": "already_running", "host": host, "port": port}

    cmd = [get_opencode_cmd(), "serve", "--port", str(port), "--hostname", host]
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
        creationflags=creationflags,
    )

    # Wait up to 10 seconds for the server to be healthy
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        if is_server_alive(host, port):
            return {
                "status": "started",
                "pid": proc.pid,
                "host": host,
                "port": port,
            }
        time.sleep(0.5)

    return {
        "status": "timeout_waiting",
        "pid": proc.pid,
        "host": host,
        "port": port,
    }


def run_prompt(
    prompt: str,
    workdir: Path | None = None,
    model: str = DEFAULT_MODEL,
    auto_approve: bool = True,
    attach: bool = True,
    timeout: float = 120.0,
    server_port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    """Execute a prompt via OpenCode headlessly and collect structured results."""
    cmd = [get_opencode_cmd(), "run"]

    if attach and is_server_alive(DEFAULT_HOST, server_port):
        cmd.extend(["--attach", f"http://{DEFAULT_HOST}:{server_port}"])

    if auto_approve:
        cmd.append("--auto")

    if model:
        cmd.extend(["-m", model])

    cmd.extend(["--format", "json", prompt])

    cwd = str(workdir.resolve()) if workdir else os.getcwd()

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )

    stdout, stderr = "", ""
    events: list[dict[str, Any]] = []
    text_parts: list[str] = []

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        return {
            "exit_code": 124,
            "success": False,
            "error": f"Command timed out after {timeout} seconds",
            "stdout": stdout,
            "stderr": stderr,
            "text": "",
        }

    # Parse JSON events from stdout
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
            events.append(ev)
            ev_type = ev.get("type")
            part = ev.get("part", {})
            if ev_type == "text" or part.get("type") == "text":
                text_content = part.get("text") or ev.get("text", "")
                if text_content:
                    text_parts.append(text_content)
        except json.JSONDecodeError:
            pass

    full_text = "".join(text_parts).strip()
    if not full_text and rc == 0:
        full_text = stdout.strip()

    return {
        "exit_code": rc,
        "success": rc == 0,
        "model": model,
        "text": full_text,
        "event_count": len(events),
        "stderr": stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Autonomous OpenCode Controller for JARVIS"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run command
    run_parser = subparsers.add_parser("run", help="Run a prompt via OpenCode")
    run_parser.add_argument("prompt", help="Prompt text to dispatch")
    run_parser.add_argument(
        "--model",
        "-m",
        default=DEFAULT_MODEL,
        help=f"Provider/model string (default: {DEFAULT_MODEL})",
    )
    run_parser.add_argument(
        "--dir", "-d", type=Path, default=None, help="Working directory"
    )
    run_parser.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=120.0,
        help="Timeout in seconds",
    )
    run_parser.add_argument(
        "--no-auto",
        action="store_true",
        help="Disable auto-approval of permissions",
    )
    run_parser.add_argument(
        "--no-attach", action="store_true", help="Do not attach to server daemon"
    )

    # server command
    server_parser = subparsers.add_parser("server", help="Manage OpenCode server")
    server_parser.add_argument(
        "action", choices=["status", "start", "stop"], help="Server action"
    )
    server_parser.add_argument(
        "--port", "-p", type=int, default=DEFAULT_PORT, help="Port to use"
    )

    args = parser.parse_args()

    if args.command == "run":
        res = run_prompt(
            prompt=args.prompt,
            workdir=args.dir,
            model=args.model,
            auto_approve=not args.no_auto,
            attach=not args.no_attach,
            timeout=args.timeout,
        )
        if res["success"]:
            print(res["text"])
            return 0
        else:
            print(f"FAILED (rc={res['exit_code']}):", file=sys.stderr)
            if res.get("error"):
                print(res["error"], file=sys.stderr)
            if res.get("stderr"):
                print(res["stderr"], file=sys.stderr)
            return res["exit_code"] or 1

    elif args.command == "server":
        if args.action == "status":
            alive = is_server_alive(DEFAULT_HOST, args.port)
            print(f"OpenCode server on {DEFAULT_HOST}:{args.port}: {'ALIVE' if alive else 'STOPPED'}")
            return 0 if alive else 1
        elif args.action == "start":
            res = start_server(DEFAULT_HOST, args.port)
            print(json.dumps(res, indent=2))
            return 0 if res["status"] in ("started", "already_running") else 1
        elif args.action == "stop":
            print("Stopping OpenCode server...")
            # On Windows, kill process listening on port
            if sys.platform == "win32":
                subprocess.run(
                    f'powershell -Command "Get-NetTCPConnection -LocalPort {args.port} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"',
                    shell=True,
                )
            print("Stopped.")
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
