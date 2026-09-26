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

    finally:
        server.stop()
