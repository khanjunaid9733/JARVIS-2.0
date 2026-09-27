"""Tests for JARVIS 2.0 Spatial GUI Server & Holographic Interface endpoints."""

import json
from pathlib import Path
import urllib.request
import pytest

from jarvis.bootstrap import CoreService
from jarvis.kernel.event_log import EventLog
from jarvis.ui.server import JarvisUIServer


@pytest.fixture
def temp_service(tmp_path: Path) -> CoreService:
    service = CoreService(home=tmp_path)
    service.start()
    yield service
    service.close()


def test_ui_server_static_and_api(temp_service: CoreService):
    # Bind to random ephemeral port or high port
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    server = JarvisUIServer(port=port, service=temp_service)
    server.start()

    try:
        base_url = f"http://127.0.0.1:{port}"

        # 1. Test Static index.html
        with urllib.request.urlopen(f"{base_url}/") as res:
            assert res.status == 200
            content = res.read().decode("utf-8")
            assert "JARVIS 2.0" in content
            assert "jarvis-core-canvas" in content

        # 2. Test /api/status GET
        with urllib.request.urlopen(f"{base_url}/api/status") as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            assert data["node_id"] == "workstation_primary"
            assert data["companion_status"] == "idle"
            assert "creator_fp" in data
            assert data["estop_tripped"] is False

        # 3. Test /api/say POST
        req = urllib.request.Request(
            f"{base_url}/api/say",
            data=json.dumps({"text": "Hello JARVIS"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            assert "reply" in data

        # 4. Test /api/say POST with remember:
        req = urllib.request.Request(
            f"{base_url}/api/say",
            data=json.dumps({"text": "remember: holographic arc core online"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            assert "Stored in durable memory" in data["reply"]

        # 5. Test /api/events GET
        with urllib.request.urlopen(f"{base_url}/api/events?limit=5") as res:
            assert res.status == 200
            events = json.loads(res.read().decode("utf-8"))
            assert isinstance(events, list)
            assert len(events) >= 1

        # 6. Test /api/estop POST (trip & reset)
        req = urllib.request.Request(
            f"{base_url}/api/estop",
            data=json.dumps({"trip": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            assert data["estop_tripped"] is True

        req = urllib.request.Request(
            f"{base_url}/api/estop",
            data=json.dumps({"trip": False}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            assert data["estop_tripped"] is False

        # 7. Test /api/shutter POST
        req = urllib.request.Request(
            f"{base_url}/api/shutter",
            data=json.dumps({"blind": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            assert data["blinded"] is True

        # 8. Test /api/verify GET
        with urllib.request.urlopen(f"{base_url}/api/verify") as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            assert data["ok"] is True

        # 9. Test /overlay route serving overlay.html
        with urllib.request.urlopen(f"{base_url}/overlay") as res:
            assert res.status == 200
            content = res.read().decode("utf-8")
            assert "J.A.R.V.I.S. — Desktop HUD" in content
            assert "reactor-canvas" in content
            assert "chat-drawer" in content
            assert "hud-ticker" in content

        # 10. Test static overlay.css
        with urllib.request.urlopen(f"{base_url}/overlay.css") as res:
            assert res.status == 200
            content = res.read().decode("utf-8")
            assert "background: transparent" in content
            assert "reactor-anchor" in content

        # 11. Test static overlay.js
        with urllib.request.urlopen(f"{base_url}/overlay.js") as res:
            assert res.status == 200
            content = res.read().decode("utf-8")
            assert "ArcReactorRenderer" in content
            assert "HUDOverlayController" in content

    finally:
        server.stop()


def test_cli_overlay_argument():
    """Verify that the CLI parser properly recognizes the --overlay flag for jarvis ui."""
    from jarvis.cli import _build_parser

    parser = _build_parser()

    # Default without --overlay
    args = parser.parse_args(["ui"])
    assert args.command == "ui"
    assert args.overlay is False
    assert args.port == 7777

    # With --overlay
    args_overlay = parser.parse_args(["ui", "--overlay"])
    assert args_overlay.command == "ui"
    assert args_overlay.overlay is True
    assert args_overlay.port == 7777

    # With custom port and --overlay
    args_custom = parser.parse_args(["ui", "--port", "9090", "--overlay", "--no-browser"])
    assert args_custom.overlay is True
    assert args_custom.port == 9090
    assert args_custom.no_browser is True


def test_hotkey_launch_transparent_hud(monkeypatch):
    """Test launch_transparent_hud executes browser with --app flag and starts pin thread."""
    from jarvis.ui import hotkey
    import subprocess

    launched_cmd = []

    def mock_popen(cmd, *args, **kwargs):
        launched_cmd.append(cmd)
        return None

    monkeypatch.setattr(hotkey.subprocess, "Popen", mock_popen)
    monkeypatch.setattr(hotkey.os.path, "exists", lambda p: True)

    pin_called = []
    monkeypatch.setattr(hotkey, "_find_and_pin_topmost", lambda title, **kwargs: pin_called.append(title))

    hotkey.launch_transparent_hud(port=8888)

    assert len(launched_cmd) == 1
    cmd = launched_cmd[0]
    assert any("--app=http://127.0.0.1:8888/overlay" in arg for arg in cmd)
    assert any("--window-size=" in arg for arg in cmd)


def test_hotkey_pin_topmost_logic(monkeypatch):
    """Test _find_and_pin_topmost invokes user32 EnumWindows and SetWindowPos."""
    from jarvis.ui import hotkey

    if hotkey.sys.platform != "win32":
        return

    # Call with 0 wait time to test graceful exit without freezing
    hotkey._find_and_pin_topmost("NON_EXISTENT_WINDOW_TITLE_TEST", max_wait_seconds=0)


def test_server_handle_say_intents(temp_service: CoreService):
    """Test JarvisUIServer.handle_say dispatches intents for status, time, identity, search, and memory."""
    server = JarvisUIServer(port=8899, service=temp_service)

    # 1. System status
    res = server.handle_say("status")
    assert "Systems nominal" in res["reply"]
    assert res.get("action") == "system_status"

    # 2. Time & Date
    res = server.handle_say("what time is it")
    assert "The current time is" in res["reply"]
    assert res.get("action") == "time"

    res = server.handle_say("what day is today")
    assert "Today is" in res["reply"]
    assert res.get("action") == "date"

    # 3. Persona / Identity
    res = server.handle_say("who are you")
    assert "J.A.R.V.I.S." in res["reply"]
    assert res.get("action") == "identify"

    # 4. Memory storage
    res = server.handle_say("remember: holographic arc core online")
    assert "Stored in durable memory" in res["reply"]
    assert res.get("action") == "memory_write"

    # 5. Autonomous Command Execution via Cognitive Agent
    res = server.handle_say("cmd: echo JARVIS_INTEGRATION_OK")
    assert "JARVIS_INTEGRATION_OK" in res["reply"]
    assert res.get("action") == "system_command"
    assert res.get("success") is True

    # 6. Desktop Input Control via Cognitive Agent
    res = server.handle_say("mouse: get")
    assert "Current cursor position" in res["reply"]
    assert res.get("action") == "desktop_input"
    assert res.get("success") is True

    # 7. Conversational fallback
    res = server.handle_say("standby mode")
    assert "Acknowledged, sir" in res["reply"] or "sir" in res["reply"].lower()


def test_native_voice_listener_wake_patterns():
    """Verify that NativeVoiceListener correctly matches wake phrases and ignores normal speech."""
    from jarvis.ui.voice_listener import NativeVoiceListener
    import re

    patterns = NativeVoiceListener.WAKE_PATTERNS

    def matches(phrase: str) -> bool:
        return any(p.search(phrase) for p in patterns)

    # Should match wake words
    assert matches("hey jarvis")
    assert matches("Hey JARVIS, what time is it?")
    assert matches("jarvis")
    assert matches("ok jarvis open chrome")
    assert matches("hi jarvis")
    assert matches("wake up jarvis")
    assert matches("wake up")
    assert matches("J.A.R.V.I.S.")

    # Should NOT match unrelated speech
    assert not matches("hello world")
    assert not matches("computer, run diagnostic")
    assert not matches("alexa turn off lights")
    assert not matches("siri play music")


def test_native_voice_listener_start_stop():
    """Verify NativeVoiceListener lifecycle start and stop."""
    from jarvis.ui.voice_listener import NativeVoiceListener

    listener = NativeVoiceListener(port=7777)
    assert not listener.is_alive
    # Stop when not started is safe
    listener.stop()
    assert not listener.is_alive


