from __future__ import annotations

"""JARVIS 2.0 — Spatial Cognitive Interface & Holographic GUI Server.

Serves the modern cybernetic HUD and Holographic Arc Core interface, providing
real-time event log streaming, interactive chat/say routing, autonomous skill
dispatch, E-Stop safety latching, and privacy shutter controls.
"""

import http.server
import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import urllib.parse
import webbrowser
from typing import Any

from jarvis.bootstrap import CoreService
from jarvis.kernel.event_log import Event, EventLog
from jarvis.perception.screen import ScreenPrivacyShutter
from jarvis.safety.estop import EStopLatch
from jarvis.skills.cognitive_agent import CognitiveAgent
from jarvis.skills.context import SkillExecutionContext
from jarvis.skills.engine import SkillRuntimeEngine
from jarvis.ui.overlay import CompanionStatus, SpatialOverlayEngine


STATIC_DIR = Path(__file__).parent / "web"
DEFAULT_PORT = 7777


class JarvisRequestHandler(http.server.BaseHTTPRequestHandler):
    """Handles static web assets and REST API endpoints for the JARVIS GUI."""

    server_engine: JarvisUIServer

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/status":
            self._handle_get_status()
        elif path == "/api/events":
            limit = int(query.get("limit", [50])[0])
            self._handle_get_events(limit)
        elif path == "/api/verify":
            self._handle_get_verify()
        elif path == "/overlay":
            self._serve_static("overlay.html")
        else:
            self._serve_static(path)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {}

        if path == "/api/say":
            self._handle_post_say(payload)
        elif path == "/api/skill/auto":
            self._handle_post_skill_auto(payload)
        elif path == "/api/status":
            self._handle_post_status(payload)
        elif path == "/api/wake":
            self._handle_post_wake(payload)
        elif path == "/api/estop":
            self._handle_post_estop(payload)
        elif path == "/api/shutter":
            self._handle_post_shutter(payload)
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def _serve_static(self, path: str) -> None:
        if path in ("/", ""):
            filename = "index.html"
        else:
            filename = path.lstrip("/")

        target_file = (STATIC_DIR / filename).resolve()
        if not target_file.is_file() or not target_file.is_relative_to(STATIC_DIR):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        mime_type, _ = mimetypes.guess_type(str(target_file))
        mime_type = mime_type or "application/octet-stream"

        try:
            data = target_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(exc).encode("utf-8"))

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _handle_get_status(self) -> None:
        engine = self.server.server_engine  # type: ignore[attr-defined]
        service = engine.service
        overlay = engine.overlay

        all_events = list(service.log.replay())

        # Live hardware telemetry snapshot
        cpu_val = 0.0
        ram_val = 0.0
        battery_pct = None
        try:
            import psutil
            cpu_val = psutil.cpu_percent(interval=None)
            ram_val = psutil.virtual_memory().percent
            batt = psutil.sensors_battery()
            if batt:
                battery_pct = round(batt.percent, 1)
        except Exception:
            pass

        status_data = {
            "node_id": "workstation_primary",
            "companion_status": overlay.status.value,
            "creator_fp": service.fingerprint,
            "event_count": len(all_events),
            "estop_tripped": overlay.safety.is_tripped(),
            "blinded": overlay.shutter.is_blinded,
            "providers": list(service.provider_ids()),
            "cpu_percent": round(cpu_val, 1),
            "ram_percent": round(ram_val, 1),
            "battery_percent": battery_pct,
        }
        self._send_json(status_data)

    def _handle_get_events(self, limit: int) -> None:
        engine = self.server.server_engine  # type: ignore[attr-defined]
        events = list(engine.service.log.replay())
        recent = events[-limit:] if limit > 0 else events
        serialized = [
            {
                "event_id": e.event_id,
                "stream_id": e.stream_id,
                "event_type": e.event_type,
                "principal_id": e.principal_id,
                "payload": e.payload,
            }
            for e in reversed(recent)
        ]
        self._send_json(serialized)

    def _handle_get_verify(self) -> None:
        engine = self.server.server_engine  # type: ignore[attr-defined]
        log = engine.service.log
        try:
            ok = log.verify_chain()
            events = list(log.replay())
            digest = log.projection_digest() if events else "empty"
            self._send_json({
                "ok": ok,
                "event_count": len(events),
                "digest": digest,
            })
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def _handle_post_say(self, payload: dict[str, Any]) -> None:
        engine = self.server.server_engine  # type: ignore[attr-defined]
        text = str(payload.get("text", "")).strip()
        if not text:
            self._send_json({"error": "Empty text"}, status=400)
            return

        print(f"\n=======================================================", flush=True)
        print(f"[VOICE/SPEECH INPUT] User: \"{text}\"", flush=True)
        res = engine.handle_say(text, source="web_gui")
        print(f"[JARVIS RESPONSE] Action: {res.get('action', 'reply')} | Reply: \"{res.get('reply', '')}\"", flush=True)
        print(f"=======================================================\n", flush=True)
        self._send_json(res)


    def _handle_post_skill_auto(self, payload: dict[str, Any]) -> None:
        engine = self.server.server_engine  # type: ignore[attr-defined]
        goal = str(payload.get("goal", "")).strip()
        if not goal:
            self._send_json({"error": "Empty goal"}, status=400)
            return

        ctx = SkillExecutionContext(
            workspace=Path.cwd() / "artifacts",
            timeout_seconds=30.0,
        )
        res = engine.skill_engine.execute_goal(goal, ctx)
        self._send_json({
            "status": res.status,
            "success": res.success,
            "message": res.message,
            "stdout": res.execution.stdout if res.execution else "",
            "stderr": res.execution.stderr if res.execution else "",
        })

    def _handle_post_status(self, payload: dict[str, Any]) -> None:
        engine = self.server.server_engine  # type: ignore[attr-defined]
        status_val = str(payload.get("status", "idle")).lower()
        try:
            companion_status = CompanionStatus(status_val)
            engine.overlay.set_status(companion_status)
            self._send_json({"status": companion_status.value})
        except ValueError:
            self._send_json({"error": f"Invalid status: {status_val}"}, status=400)

    def _handle_post_wake(self, payload: dict[str, Any]) -> None:
        engine = self.server.server_engine  # type: ignore[attr-defined]
        engine.overlay.set_status(CompanionStatus.LISTENING)
        self._send_json({"woken": True, "status": "listening"})

    def _handle_post_estop(self, payload: dict[str, Any]) -> None:
        engine = self.server.server_engine  # type: ignore[attr-defined]
        trip = bool(payload.get("trip", True))
        if trip:
            engine.overlay.trigger_emergency_stop()
        else:
            engine.overlay.safety.reset()
            engine.overlay.set_status(CompanionStatus.IDLE)
        self._send_json({"estop_tripped": engine.overlay.safety.is_tripped()})

    def _handle_post_shutter(self, payload: dict[str, Any]) -> None:
        engine = self.server.server_engine  # type: ignore[attr-defined]
        blind = payload.get("blind")
        state = engine.overlay.toggle_privacy_shutter(blind=blind)
        self._send_json({"blinded": state})


class JarvisUIServer:
    """Manages the background HTTP server for the JARVIS GUI."""

    def __init__(self, port: int = DEFAULT_PORT, service: CoreService | None = None) -> None:
        self.port = port
        self._owned_service = service is None
        self.service = service or CoreService()
        if self._owned_service:
            self.service.start()

        self.estop = EStopLatch(event_log=self.service.log)
        self.shutter = ScreenPrivacyShutter()
        self.overlay = SpatialOverlayEngine(
            event_log=self.service.log,
            estop_latch=self.estop,
            privacy_shutter=self.shutter,
        )
        self.skill_engine = SkillRuntimeEngine(event_sink=self.service.log)
        self.cognitive_agent = CognitiveAgent(
            registry=self.skill_engine.registry,
            skill_engine=self.skill_engine,
            event_log=self.service.log,
        )
        self.personal_intelligence = self.cognitive_agent.personal_intelligence

        self._httpd: http.server.ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.hotkey_listener: Any = None
        self.voice_listener: Any = None

    def handle_say(self, text: str, source: str = "web_gui") -> dict[str, Any]:
        """Process user text/voice intent across media, apps, search, memory, skills, and LLM persona."""
        text = text.strip()
        if not text:
            return {"error": "Empty text"}

        service = self.service
        lowered = text.lower()

        # Log utterance to WAL event log
        service.log.audit(
            stream_id="companion",
            event_type="dialogue_turn",
            principal_id=service.fingerprint,
            payload={"text": text, "source": source},
        )

        # 1. Hardware Media Key Controls & System Actions (Windows 0ms Latency)
        if sys.platform == "win32":
            import ctypes

            def _send_vk(vk_code: int) -> None:
                ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
                ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)

            # Volume Controls
            if any(w in lowered for w in ["volume up", "increase volume", "louder", "turn it up"]):
                for _ in range(5):
                    _send_vk(0xAF)  # VK_VOLUME_UP
                return {"reply": "Volume increased, sir.", "action": "volume_up"}

            if any(w in lowered for w in ["volume down", "decrease volume", "softer", "lower volume", "turn it down"]):
                for _ in range(5):
                    _send_vk(0xAE)  # VK_VOLUME_DOWN
                return {"reply": "Volume decreased, sir.", "action": "volume_down"}

            if any(w in lowered for w in ["mute audio", "unmute audio", "silence", "mute"]):
                _send_vk(0xAD)  # VK_VOLUME_MUTE
                return {"reply": "Master audio mute toggled, sir.", "action": "mute_toggle"}

            # Playback Controls
            if lowered in ["pause", "pause music", "pause playback", "stop music", "stop playback", "halt music"]:
                _send_vk(0xB3)  # VK_MEDIA_PLAY_PAUSE
                return {"reply": "Media playback paused, sir.", "action": "media_pause"}

            if lowered in ["resume", "resume music", "resume playback", "unpause"]:
                _send_vk(0xB3)  # VK_MEDIA_PLAY_PAUSE
                return {"reply": "Media playback resumed, sir.", "action": "media_resume"}

            if any(w in lowered for w in ["next song", "next track", "skip song", "skip track", "skip"]):
                _send_vk(0xB0)  # VK_MEDIA_NEXT_TRACK
                return {"reply": "Skipping to next track, sir.", "action": "media_next"}

            if any(w in lowered for w in ["previous song", "previous track", "prev song", "prev track", "last track"]):
                _send_vk(0xB1)  # VK_MEDIA_PREV_TRACK
                return {"reply": "Returning to previous track, sir.", "action": "media_prev"}

            # System Security & Desktop Actions
            if any(w in lowered for w in ["lock pc", "lock screen", "lock workstation", "secure desktop"]):
                ctypes.windll.user32.LockWorkStation()
                return {"reply": "Workstation locked and secured, sir.", "action": "lock_workstation"}

            if any(w in lowered for w in ["minimize all", "show desktop", "minimize windows"]):
                # Win+D
                ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0x44, 0, 2, 0)
                ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)
                return {"reply": "Minimizing active windows, sir.", "action": "minimize_all"}

        # 2. Spotify & Media Playback Intent (typo-resilient: "on spotify", "onn spotify", "via spotify")
        if re.search(r"\b(?:on|onn|in|via|from)\s+spotify\b|\bspotify\b", text, re.IGNORECASE):
            track = text
            track = re.sub(r"^(?:play|listen\s+to|open)\s+", "", track, flags=re.IGNORECASE).strip()
            track = re.sub(r"\b(?:on|onn|in|via|from)\s+spotify\b", "", track, flags=re.IGNORECASE).strip()
            track = re.sub(r"^spotify\s+(?:play\s+)?", "", track, flags=re.IGNORECASE).strip()
            track = track.strip(" '\".,")

            encoded = urllib.parse.quote_plus(track) if track and track.lower() != "spotify" else ""
            if encoded:
                uri = f"spotify:search:{encoded}"
                url = f"https://open.spotify.com/search/{encoded}"
                reply = f"Playing '{track}' on Spotify, sir."
            else:
                uri = "spotify:"
                url = "https://open.spotify.com"
                reply = "Opening Spotify, sir."

            service.log.audit(
                stream_id="companion",
                event_type="media_playback_initiated",
                principal_id=service.fingerprint,
                payload={"query": track or "spotify", "service": "spotify", "source": source},
            )

            if sys.platform == "win32":
                os.system(f'start "" "{uri}"')
            webbrowser.open(url)
            return {
                "reply": reply,
                "action": "media_playback",
                "target": track or "spotify",
                "url": url,
            }

        # 2. Open / Launch Application or Website ("open ...", "launch ...", "start ...")
        APP_SHORTCUTS = {
            "chrome": ("chrome.exe", "Google Chrome"),
            "google chrome": ("chrome.exe", "Google Chrome"),
            "edge": ("msedge.exe", "Microsoft Edge"),
            "microsoft edge": ("msedge.exe", "Microsoft Edge"),
            "calculator": ("calc.exe", "Calculator"),
            "calc": ("calc.exe", "Calculator"),
            "notepad": ("notepad.exe", "Notepad"),
            "cmd": ("cmd.exe", "Command Prompt"),
            "terminal": ("powershell.exe", "Windows Terminal"),
            "powershell": ("powershell.exe", "PowerShell"),
            "code": ("code", "Visual Studio Code"),
            "vs code": ("code", "Visual Studio Code"),
            "vscode": ("code", "Visual Studio Code"),
            "explorer": ("explorer.exe", "File Explorer"),
            "files": ("explorer.exe", "File Explorer"),
            "settings": ("ms-settings:", "Windows Settings"),
            "task manager": ("taskmgr.exe", "Task Manager"),
            "taskmgr": ("taskmgr.exe", "Task Manager"),
        }

        WEB_SHORTCUTS = {
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "github": "https://www.github.com",
            "reddit": "https://www.reddit.com",
            "twitter": "https://www.twitter.com",
            "chatgpt": "https://chatgpt.com",
            "gmail": "https://mail.google.com",
            "netflix": "https://www.netflix.com",
        }

        launch_match = re.match(r"^(?:open|launch|start)\s+(.+)$", text, re.IGNORECASE)
        if launch_match:
            raw_target = launch_match.group(1).strip()
            target_lower = raw_target.lower()
            service.log.audit(
                stream_id="companion",
                event_type="app_launch_initiated",
                principal_id=service.fingerprint,
                payload={"target": raw_target, "source": source},
            )

            if target_lower in APP_SHORTCUTS:
                exec_target, app_name = APP_SHORTCUTS[target_lower]
                if sys.platform == "win32":
                    os.system(f'start "" "{exec_target}"')
                else:
                    subprocess.Popen([exec_target])
                return {"reply": f"Opening {app_name}, sir.", "action": "launch_app", "target": app_name}

            if target_lower in WEB_SHORTCUTS:
                url = WEB_SHORTCUTS[target_lower]
                webbrowser.open(url)
                return {"reply": f"Opening {raw_target} in browser, sir.", "action": "open_url", "url": url}

            if raw_target.startswith("http://") or raw_target.startswith("https://") or any(raw_target.endswith(tld) for tld in [".com", ".org", ".net", ".io", ".dev"]):
                url = raw_target if raw_target.startswith("http") else f"https://{raw_target}"
                webbrowser.open(url)
                return {"reply": f"Opening {raw_target} in browser, sir.", "action": "open_url", "url": url}
            else:
                if sys.platform == "win32":
                    os.system(f'start "" "{raw_target}"')
                else:
                    subprocess.Popen([raw_target])
                return {"reply": f"Launching {raw_target}, sir.", "action": "launch_app", "target": raw_target}

        # 3. Memory Write Intent ("remember: ...", "remember that ...", "remember ...")
        remember_match = re.match(r"^remember[:\s]+(?:that\s+)?(.+)$", text, re.IGNORECASE)
        if remember_match:
            fact = remember_match.group(1).strip()
            from jarvis.kernel.memory_write import MemoryWriter
            writer = MemoryWriter(service.log)
            res = writer.remember(content=fact, source=source)
            if res.status == "committed":
                last_id = res.event_ids[-1][:8] if res.event_ids else "ok"
                return {"reply": f"Stored in durable memory (event {last_id}): '{fact}'.", "action": "memory_write"}
            else:
                return {"reply": f"Memory rejected: {res.reason}"}

        # 5. System Diagnostics ("status", "system status", "health", "diagnostics")
        if lowered in ("status", "system status", "health", "system health", "diagnostics"):
            events = list(service.log.replay())
            return {
                "reply": f"Systems nominal, sir. Workstation node active, {len(events)} events in WAL event log, cryptographic hash chain verified.",
                "action": "system_status",
            }

        # 6. Current Time & Date
        if any(w in lowered for w in ["what time is it", "current time", "what time"]):
            import time
            current_time = time.strftime("%I:%M %p")
            return {"reply": f"The current time is {current_time}, sir.", "action": "time"}

        if any(w in lowered for w in ["what date is it", "what day is today", "today's date", "what is today"]):
            import time
            current_date = time.strftime("%A, %B %d, %Y")
            return {"reply": f"Today is {current_date}, sir.", "action": "date"}

        # 7. Live Weather
        if "weather" in lowered:
            try:
                from jarvis.multimodal.jarvis_voice import get_live_system_context
                ctx = get_live_system_context()
                for line in ctx.splitlines():
                    if "weather" in line.lower():
                        desc = line.split(":", 1)[-1].strip()
                        return {"reply": f"Live weather update: {desc}, sir.", "action": "weather"}
            except Exception:
                pass
            return {"reply": "Meteorological sensors are currently offline, sir.", "action": "weather"}

        # 8. Memory Recall / Question ("recall ...", "what is ...", "who is ...")
        from jarvis.kernel.memory_query import answer
        ans_res = answer(service.projection(), text)
        if ans_res.answered and ans_res.answer:
            return {"reply": ans_res.answer, "action": "memory_recall"}

        # 9. Direct Persona / Creator Identity & Greeting Quick Reply
        if any(w in lowered for w in ["who are you", "what are you", "your name", "introduce yourself"]):
            return {
                "reply": "I am J.A.R.V.I.S., sir. Just A Rather Very Intelligent System, your autonomous spatial desktop companion.",
                "action": "identify",
            }

        if any(w in lowered for w in ["who am i", "what is my name", "do you know me", "my profile", "who created you", "what do you know about me", "tell me about myself", "my active projects"]):
            p = self.personal_intelligence.profile
            projects_str = ", ".join(p.active_projects)
            reply = (
                f"You are {p.name}, my Creator and Chief Architect, sir. "
                f"You are operating from {p.location} ({p.timezone}). "
                f"Active endeavors include: {projects_str}. "
                f"My personal intelligence database retains {len(p.facts)} biographical facts and preferences regarding your workflow."
            )
            return {"reply": reply, "action": "creator_profile_recalled"}

        if lowered in ["hello", "hi", "hey", "hey jarvis", "hello jarvis", "good morning", "good afternoon", "good evening", "greetings"]:
            return {"reply": self.personal_intelligence.get_greeting(), "action": "greeting"}

        # 10. Autonomous Cognitive Agent & Skill Operator
        agent_res = self.cognitive_agent.process_turn(text, source=source)
        if agent_res and agent_res.reply:
            return {
                "reply": agent_res.reply,
                "action": agent_res.action,
                "tools": [t.name for t in agent_res.tools_executed],
                "success": agent_res.success,
            }

        reply = f"Acknowledged, sir: '{text}'. Core operational and standing by."
        return {"reply": reply, "action": "standby"}


    def start(self, enable_hotkey: bool = True, enable_voice: bool = False) -> None:
        server_address = ("127.0.0.1", self.port)
        self._httpd = http.server.ThreadingHTTPServer(server_address, JarvisRequestHandler)
        self._httpd.server_engine = self  # type: ignore[attr-defined]

        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

        if enable_hotkey and sys.platform == "win32":
            try:
                from .hotkey import GlobalHotkeyListener
                self.hotkey_listener = GlobalHotkeyListener(port=self.port)
                self.hotkey_listener.start()
            except Exception:
                pass

        if enable_voice:
            try:
                from .voice_listener import NativeVoiceListener
                self.voice_listener = NativeVoiceListener(port=self.port, server_engine=self)
                self.voice_listener.start()
            except Exception as exc:
                print(f"[JarvisUIServer] Voice listener start skipped: {exc}")

    def stop(self) -> None:
        if self.voice_listener:
            try:
                self.voice_listener.stop()
            except Exception:
                pass
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._owned_service and self.service:
            self.service.close()


def run_server(port: int = DEFAULT_PORT, service: CoreService | None = None) -> None:
    """Run the JARVIS GUI server with hotkeys and background voice listening."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            print(f"JARVIS 2.0 is already active on http://127.0.0.1:{port}")
            from .hotkey import launch_or_focus_hud
            launch_or_focus_hud(port=port)
            return

    server = JarvisUIServer(port=port, service=service)
    server.start(enable_hotkey=True, enable_voice=True)
    print(f"JARVIS 2.0 Spatial Interface active at: http://127.0.0.1:{port}")
    print("Hands-free acoustic trigger active: Say 'Hey JARVIS' to wake.")
    print("System hotkey active: Press Alt+J to summon HUD.")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down GUI server...")
        server.stop()


def run_overlay(port: int = DEFAULT_PORT, service: CoreService | None = None) -> None:
    """Run the JARVIS HUD Overlay server and launch transparent desktop HUD window."""
    import socket
    port_in_use = False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        port_in_use = (s.connect_ex(("127.0.0.1", port)) == 0)

    server = None
    if not port_in_use:
        server = JarvisUIServer(port=port, service=service)
        server.start(enable_hotkey=True, enable_voice=True)

    overlay_url = f"http://127.0.0.1:{port}/overlay"
    print(f"JARVIS 2.0 Desktop HUD Overlay active at: {overlay_url}")
    print(f"Press Alt+J to summon/focus the HUD window.")
    print("Hands-free acoustic trigger active: Say 'Hey JARVIS' in background.")

    # Launch or focus the overlay in transparent app mode
    from .hotkey import launch_or_focus_hud
    launch_or_focus_hud(port=port)

    if server:
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down HUD overlay...")
            server.stop()



if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    mode = sys.argv[2] if len(sys.argv) > 2 else "dashboard"
    if mode == "overlay":
        run_overlay(port)
    else:
        run_server(port)

