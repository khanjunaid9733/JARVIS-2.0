from __future__ import annotations

"""M5.2 External Node Protocol & Lightweight RPC Seam Tests (tests/nodes/test_node_rpc.py).

Validates:
1. test_pairing_success_with_valid_code
2. test_pairing_rejected_with_invalid_code
3. test_pairing_rejected_when_code_expired
4. test_rpc_dispatch_and_response_roundtrip
5. test_rpc_unknown_node_raises_or_fails
6. test_heartbeat_updates_last_seen
7. test_heartbeat_timeout_transitions_to_hold
8. test_capability_filtering
"""

import json
import time
from dataclasses import asdict
from datetime import datetime, timezone

import pytest

from jarvis.nodes.protocol import (
    HeartbeatPacket,
    NodeCapability,
    NodeType,
    PairingRequest,
    PairingState,
    RPCResponse,
)
from jarvis.nodes.rpc_adapter import (
    InMemoryNodeTransport,
    NodeManager,
)


@pytest.fixture
def transport() -> InMemoryNodeTransport:
    return InMemoryNodeTransport()


@pytest.fixture
def manager(transport: InMemoryNodeTransport) -> NodeManager:
    return NodeManager(transport=transport)


@pytest.fixture
def sample_capabilities() -> tuple[NodeCapability, ...]:
    return (
        NodeCapability(
            name="telemetry.read",
            version="1.0.0",
            description="Read device telemetry",
            required_permissions=("telemetry:read",),
        ),
        NodeCapability(
            name="motor.actuate",
            version="1.0.0",
            description="Control motor position",
            required_permissions=("actuation:write",),
            effect_types=("physical_actuation",),
        ),
    )


def test_pairing_success_with_valid_code(
    manager: NodeManager, sample_capabilities: tuple[NodeCapability, ...]
) -> None:
    code = "TEST-PAIR"
    manager.register_pairing_code(code, ttl_seconds=60.0)

    req = PairingRequest(
        node_id="phone-node-01",
        name="Junaid's Phone",
        node_type=NodeType.PHONE,
        capabilities=sample_capabilities,
        public_key="ed25519-pubkey-abc123xyz",
        pairing_code=code,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    resp = manager.handle_pairing_request(req)

    assert resp.success is True
    assert resp.node_id == "phone-node-01"
    assert resp.state == PairingState.PAIRED
    assert len(resp.session_token) > 0
    assert resp.error_message == ""

    # NodeSpec should be registered
    node = manager.get_node("phone-node-01")
    assert node is not None
    assert node.name == "Junaid's Phone"
    assert len(node.capabilities) == 2
    assert manager.get_node_state("phone-node-01") == PairingState.PAIRED


def test_pairing_rejected_with_invalid_code(
    manager: NodeManager, sample_capabilities: tuple[NodeCapability, ...]
) -> None:
    manager.register_pairing_code("VALID-CODE", ttl_seconds=60.0)

    req = PairingRequest(
        node_id="phone-node-02",
        name="Rogue Device",
        node_type=NodeType.PHONE,
        capabilities=sample_capabilities,
        public_key="pubkey-fake",
        pairing_code="WRONG-CODE",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    resp = manager.handle_pairing_request(req)

    assert resp.success is False
    assert resp.node_id == "phone-node-02"
    assert resp.state == PairingState.UNPAIRED
    assert "invalid" in resp.error_message.lower()
    assert manager.get_node("phone-node-02") is None


def test_pairing_rejected_when_code_expired(
    manager: NodeManager, sample_capabilities: tuple[NodeCapability, ...]
) -> None:
    code = "EXP-CODE"
    # Register with negative/zero TTL to simulate immediate expiration
    manager.register_pairing_code(code, ttl_seconds=-1.0)

    req = PairingRequest(
        node_id="phone-node-03",
        name="Expired Attempt",
        node_type=NodeType.PHONE,
        capabilities=sample_capabilities,
        public_key="pubkey-3",
        pairing_code=code,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    resp = manager.handle_pairing_request(req)

    assert resp.success is False
    assert resp.state == PairingState.EXPIRED
    assert "expired" in resp.error_message.lower()
    assert manager.get_node("phone-node-03") is None


def test_rpc_dispatch_and_response_roundtrip(
    manager: NodeManager,
    transport: InMemoryNodeTransport,
    sample_capabilities: tuple[NodeCapability, ...],
) -> None:
    # Pair node first
    manager.register_pairing_code("CODE-RPC", ttl_seconds=60.0)
    req = PairingRequest(
        node_id="robot-arm-01",
        name="Robotic Arm Node",
        node_type=NodeType.EMBEDDED_ROBOT,
        capabilities=sample_capabilities,
        public_key="pubkey-robot",
        pairing_code="CODE-RPC",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    manager.handle_pairing_request(req)

    # Simulate node responding to RPC in background or deliver before receive
    # We inspect the sent message from transport and simulate answering it
    def simulate_node_reply():
        sent = transport.get_sent_messages("robot-arm-01")
        if sent:
            parsed = json.loads(sent[-1])
            req_id = parsed["request_id"]
            reply = RPCResponse(
                request_id=req_id,
                success=True,
                result={"angle": 45.0, "status": "actuated"},
            )
            transport.deliver_to_manager("robot-arm-01", json.dumps(asdict(reply)))

    # Hook transport.send to automatically reply
    orig_send = transport.send
    def send_and_reply(node_id: str, payload: str):
        orig_send(node_id, payload)
        parsed = json.loads(payload)
        reply = RPCResponse(
            request_id=parsed["request_id"],
            success=True,
            result={"position": [10, 20, 30]},
        )
        transport.deliver_to_manager(node_id, json.dumps(asdict(reply)))

    transport.send = send_and_reply  # type: ignore[assignment]

    resp = manager.dispatch_rpc(
        node_id="robot-arm-01",
        method="motor.actuate",
        params={"speed": 100},
        timeout=2.0,
    )

    assert resp.success is True
    assert resp.result == {"position": [10, 20, 30]}
    assert resp.error_code == 0


def test_rpc_unknown_node_raises_or_fails(manager: NodeManager) -> None:
    resp = manager.dispatch_rpc(
        node_id="unknown-ghost-node",
        method="telemetry.read",
        params={},
        timeout=1.0,
    )

    assert resp.success is False
    assert resp.error_code == 404
    assert "not paired" in resp.error_message.lower() or "not found" in resp.error_message.lower()


def test_heartbeat_updates_last_seen(
    manager: NodeManager, sample_capabilities: tuple[NodeCapability, ...]
) -> None:
    manager.register_pairing_code("HB-CODE", ttl_seconds=60.0)
    req = PairingRequest(
        node_id="sensor-01",
        name="Temp Sensor",
        node_type=NodeType.SENSOR_NODE,
        capabilities=sample_capabilities,
        public_key="pubkey-sensor",
        pairing_code="HB-CODE",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    manager.handle_pairing_request(req)

    initial_node = manager.get_node("sensor-01")
    assert initial_node is not None
    initial_last_seen = initial_node.last_seen

    # Heartbeat on unpaired node fails
    bad_hb = HeartbeatPacket(node_id="nonexistent", sequence=1, timestamp=datetime.now(timezone.utc).isoformat())
    assert manager.record_heartbeat(bad_hb) is False

    # Heartbeat on paired node succeeds
    time.sleep(0.01)
    good_hb = HeartbeatPacket(node_id="sensor-01", sequence=1, timestamp=datetime.now(timezone.utc).isoformat())
    assert manager.record_heartbeat(good_hb) is True

    updated_node = manager.get_node("sensor-01")
    assert updated_node is not None
    assert updated_node.last_seen >= initial_last_seen


def test_heartbeat_timeout_transitions_to_hold(
    manager: NodeManager, sample_capabilities: tuple[NodeCapability, ...]
) -> None:
    manager.register_pairing_code("HB-TIMEOUT-CODE", ttl_seconds=60.0)
    req = PairingRequest(
        node_id="iot-device-99",
        name="Remote Switch",
        node_type=NodeType.IOT_PERIPHERAL,
        capabilities=sample_capabilities,
        public_key="pubkey-iot",
        pairing_code="HB-TIMEOUT-CODE",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    manager.handle_pairing_request(req)
    assert manager.get_node_state("iot-device-99") == PairingState.PAIRED

    # Check timeout with 0.0s threshold to trigger immediately
    timed_out = manager.check_heartbeat_timeouts(timeout_seconds=-0.1)

    assert "iot-device-99" in timed_out
    assert manager.get_node_state("iot-device-99") == PairingState.REVOKED

    # Dispatches to a revoked node should now fail-closed
    resp = manager.dispatch_rpc("iot-device-99", "telemetry.read", timeout=0.5)
    assert resp.success is False
    assert resp.error_code == 404


def test_capability_filtering(
    manager: NodeManager, sample_capabilities: tuple[NodeCapability, ...]
) -> None:
    manager.register_pairing_code("CAP-CODE", ttl_seconds=60.0)
    req = PairingRequest(
        node_id="camera-node-01",
        name="Security Camera",
        node_type=NodeType.SENSOR_NODE,
        capabilities=sample_capabilities,  # Only telemetry.read and motor.actuate
        public_key="pubkey-camera",
        pairing_code="CAP-CODE",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    manager.handle_pairing_request(req)

    # Calling an unauthorized / undeclared capability should be rejected fail-closed
    resp = manager.dispatch_rpc(
        node_id="camera-node-01",
        method="unauthorized.reboot_system",
        params={},
        timeout=1.0,
    )

    assert resp.success is False
    assert resp.error_code == 403
    assert "not supported" in resp.error_message.lower()
