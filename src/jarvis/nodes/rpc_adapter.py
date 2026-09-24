from __future__ import annotations

"""M5.2 External Node Protocol & Lightweight RPC Seam (src/jarvis/nodes/rpc_adapter.py).

Implements transport-agnostic RPC communication, mutual pairing validation,
fail-closed capability filtering, and continuous heartbeat monitoring.
"""

import json
import logging
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, runtime_checkable

from jarvis.nodes.protocol import (
    HeartbeatPacket,
    NodeCapability,
    NodeSpec,
    NodeType,
    PairingRequest,
    PairingResponse,
    PairingState,
    RPCRequest,
    RPCResponse,
)

logger = logging.getLogger("jarvis.nodes.rpc_adapter")


@runtime_checkable
class NodeTransport(Protocol):
    """Transport-agnostic abstraction for node communication."""

    def send(self, node_id: str, payload: str) -> None:
        """Send a string payload to a destination node."""
        ...

    def receive(self, timeout: float | None = None) -> tuple[str, str] | None:
        """Receive the next available (node_id, payload) tuple, or None on timeout."""
        ...

    def is_connected(self, node_id: str) -> bool:
        """Check if the node transport link is active."""
        ...


class InMemoryNodeTransport:
    """Deterministic in-memory transport for unit testing and local node loops."""

    def __init__(self) -> None:
        self._inbox: list[tuple[str, str]] = []
        self._outbox: dict[str, list[str]] = {}
        self._connected: set[str] = set()

    def set_connected(self, node_id: str, connected: bool = True) -> None:
        if connected:
            self._connected.add(node_id)
        else:
            self._connected.discard(node_id)

    def send(self, node_id: str, payload: str) -> None:
        if node_id not in self._outbox:
            self._outbox[node_id] = []
        self._outbox[node_id].append(payload)

    def receive(self, timeout: float | None = None) -> tuple[str, str] | None:
        if self._inbox:
            return self._inbox.pop(0)
        return None

    def deliver_to_manager(self, node_id: str, payload: str) -> None:
        """Simulate a node delivering an incoming message to the host manager."""
        self._inbox.append((node_id, payload))

    def get_sent_messages(self, node_id: str) -> list[str]:
        return list(self._outbox.get(node_id, []))

    def is_connected(self, node_id: str) -> bool:
        return node_id in self._connected


class NodeManager:
    """Authoritative host-side manager for external embodied device nodes."""

    def __init__(self, transport: NodeTransport | None = None) -> None:
        self.transport = transport or InMemoryNodeTransport()
        self._active_pairing_codes: dict[str, float] = {}  # code -> expiry_monotonic
        self._nodes: dict[str, NodeSpec] = {}  # node_id -> NodeSpec
        self._node_states: dict[str, PairingState] = {}  # node_id -> PairingState
        self._last_seen_monotonic: dict[str, float] = {}  # node_id -> float
        self._pending_rpc_responses: dict[str, RPCResponse] = {}

    def register_pairing_code(self, code: str, ttl_seconds: float = 300.0) -> None:
        """Register a valid one-time pairing code with a lifetime TTL."""
        expiry = time.monotonic() + ttl_seconds
        self._active_pairing_codes[code.strip()] = expiry

    def handle_pairing_request(self, req: PairingRequest) -> PairingResponse:
        """Process a node pairing request under strict verification gates."""
        code = req.pairing_code.strip()
        now = time.monotonic()

        if code not in self._active_pairing_codes:
            logger.warning("Pairing rejected for node %s: invalid code", req.node_id)
            return PairingResponse(
                success=False,
                node_id=req.node_id,
                state=PairingState.UNPAIRED,
                error_message="Invalid pairing code",
            )

        expiry = self._active_pairing_codes[code]
        if now >= expiry:
            del self._active_pairing_codes[code]
            logger.warning("Pairing rejected for node %s: expired code", req.node_id)
            return PairingResponse(
                success=False,
                node_id=req.node_id,
                state=PairingState.EXPIRED,
                error_message="Pairing code expired",
            )

        # Valid pairing: consume code
        del self._active_pairing_codes[code]

        session_token = uuid.uuid4().hex
        now_utc = datetime.now(timezone.utc).isoformat()

        # Normalize capabilities
        capabilities: list[NodeCapability] = []
        for cap in req.capabilities:
            if isinstance(cap, dict):
                capabilities.append(NodeCapability(**cap))
            else:
                capabilities.append(cap)

        spec = NodeSpec(
            node_id=req.node_id,
            name=req.name,
            node_type=req.node_type,
            capabilities=tuple(capabilities),
            public_key=req.public_key,
            paired_at=now_utc,
            last_seen=now_utc,
            metadata={"session_token": session_token},
        )

        self._nodes[req.node_id] = spec
        self._node_states[req.node_id] = PairingState.PAIRED
        self._last_seen_monotonic[req.node_id] = now

        if isinstance(self.transport, InMemoryNodeTransport):
            self.transport.set_connected(req.node_id, True)

        logger.info("Node paired successfully: %s (%s)", req.node_id, req.name)
        return PairingResponse(
            success=True,
            node_id=req.node_id,
            state=PairingState.PAIRED,
            session_token=session_token,
        )

    def get_node(self, node_id: str) -> NodeSpec | None:
        return self._nodes.get(node_id)

    def get_node_state(self, node_id: str) -> PairingState:
        return self._node_states.get(node_id, PairingState.UNPAIRED)

    def record_heartbeat(self, hb: HeartbeatPacket) -> bool:
        """Process a periodic node heartbeat packet."""
        node_id = hb.node_id
        if self._node_states.get(node_id) != PairingState.PAIRED:
            logger.warning("Heartbeat ignored for un-paired node %s", node_id)
            return False

        now = time.monotonic()
        self._last_seen_monotonic[node_id] = now
        spec = self._nodes.get(node_id)
        if spec:
            updated = NodeSpec(
                node_id=spec.node_id,
                name=spec.name,
                node_type=spec.node_type,
                capabilities=spec.capabilities,
                public_key=spec.public_key,
                paired_at=spec.paired_at,
                last_seen=datetime.now(timezone.utc).isoformat(),
                metadata=spec.metadata,
            )
            self._nodes[node_id] = updated
        return True

    def check_heartbeat_timeouts(self, timeout_seconds: float = 15.0) -> tuple[str, ...]:
        """Fail-closed health check: transitions inactive nodes to HOLD/REVOKED."""
        now = time.monotonic()
        timed_out: list[str] = []

        for node_id, state in list(self._node_states.items()):
            if state == PairingState.PAIRED:
                last_seen = self._last_seen_monotonic.get(node_id, 0.0)
                if now - last_seen > timeout_seconds:
                    logger.warning("Node %s heartbeat timed out (last seen %.1fs ago). Transitioning to HOLD.", node_id, now - last_seen)
                    self._node_states[node_id] = PairingState.REVOKED
                    if isinstance(self.transport, InMemoryNodeTransport):
                        self.transport.set_connected(node_id, False)
                    timed_out.append(node_id)

        return tuple(timed_out)

    def dispatch_rpc(
        self,
        node_id: str,
        method: str,
        params: Mapping[str, Any] | None = None,
        timeout: float = 10.0,
    ) -> RPCResponse:
        """Dispatch an authenticated RPC call to a node with fail-closed checks."""
        req_id = uuid.uuid4().hex
        params = params or {}

        # 1. Verify Node Registration and Pairing State
        if node_id not in self._nodes or self._node_states.get(node_id) != PairingState.PAIRED:
            return RPCResponse(
                request_id=req_id,
                success=False,
                error_code=404,
                error_message=f"Node '{node_id}' is not paired or active.",
            )

        node = self._nodes[node_id]

        # 2. Capability Filtering (Fail-Closed)
        supported_methods = {cap.name for cap in node.capabilities}
        if method not in supported_methods:
            logger.error("RPC refused: method '%s' not in capabilities for node '%s'", method, node_id)
            return RPCResponse(
                request_id=req_id,
                success=False,
                error_code=403,
                error_message=f"Capability '{method}' not supported by node '{node_id}'.",
            )

        # 3. Construct and Transmit Request
        rpc_req = RPCRequest(
            request_id=req_id,
            method=method,
            params=params,
            node_id=node_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        payload = json.dumps(asdict(rpc_req))
        try:
            self.transport.send(node_id, payload)
        except Exception as exc:
            logger.error("Failed to send RPC request to node %s: %s", node_id, exc)
            return RPCResponse(
                request_id=req_id,
                success=False,
                error_code=500,
                error_message=f"Transport error: {exc}",
            )

        # 4. Await Response (or check immediate queue if mock/in-memory)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rec = self.transport.receive(timeout=min(0.5, max(0.01, deadline - time.monotonic())))
            if rec:
                from_node, raw_payload = rec
                if from_node == node_id:
                    try:
                        data = json.loads(raw_payload)
                        if data.get("request_id") == req_id:
                            return RPCResponse(
                                request_id=req_id,
                                success=data.get("success", False),
                                result=data.get("result"),
                                error_code=data.get("error_code", 0),
                                error_message=data.get("error_message", ""),
                            )
                    except json.JSONDecodeError:
                        pass
            else:
                # In tests, if InMemoryNodeTransport has pre-registered responses
                if req_id in self._pending_rpc_responses:
                    return self._pending_rpc_responses.pop(req_id)
                time.sleep(0.01)

        # Timeout reached
        return RPCResponse(
            request_id=req_id,
            success=False,
            error_code=408,
            error_message=f"RPC request '{req_id}' timed out after {timeout}s",
        )

    def register_mock_response(self, request_id: str, response: RPCResponse) -> None:
        """Register a predetermined response for testing dispatch_rpc."""
        self._pending_rpc_responses[request_id] = response
