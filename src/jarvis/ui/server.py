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
import sys
import threading
import urllib.parse
from typing import Any

from jarvis.bootstrap import CoreService
from jarvis.kernel.event_log import Event, EventLog
from jarvis.perception.screen import ScreenPrivacyShutter
from jarvis.safety.estop import EStopLatch
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
        status_data = {
            "node_id": "workstation_primary",
            "companion_status": overlay.status.value,
            "creator_fp": service.fingerprint,
            "event_count": len(all_events),
            "estop_tripped": overlay.safety.is_tripped(),
            "blinded": overlay.shutter.is_blinded,
            "providers": list(service.provider_ids()),
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

        service = engine.service
        # Check if remember command
        if text.lower().startswith("remember:"):
            from jarvis.kernel.memory_write import MemoryWriter
            fact = text.split(":", 1)[1].strip()
            writer = MemoryWriter(service.log)
            res = writer.remember(content=fact, source="web_gui")
            if res.status == "committed":
                last_id = res.event_ids[-1][:8] if res.event_ids else "ok"
                self._send_json({"reply": f"Stored in durable memory (event {last_id})."})
            else:
                self._send_json({"reply": f"Memory rejected: {res.reason}"})
            return

        # Regular question/utterance
        from jarvis.kernel.memory_query import answer
        ans_res = answer(service.projection(), text)
        if ans_res.answered and ans_res.answer:
            reply = ans_res.answer
        else:
            reply = f"Acknowledged: '{text}'. Core operational."
        self._send_json({"reply": reply})

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

        self._httpd: http.server.HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.hotkey_listener: Any = None

    def start(self, enable_hotkey: bool = True) -> None:
        server_address = ("127.0.0.1", self.port)
        self._httpd = http.server.HTTPServer(server_address, JarvisRequestHandler)
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

    def stop(self) -> None:
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
    """Run the JARVIS GUI server synchronously in the foreground."""
    server = JarvisUIServer(port=port, service=service)
    server.start()
    print(f"JARVIS 2.0 Spatial Interface active at: http://127.0.0.1:{port}")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down GUI server...")
        server.stop()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    run_server(port)
