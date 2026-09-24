# M5.2 — External Node Protocol & Lightweight RPC Seam (Kickoff & Design Contract)

**Status:** ACCEPTED DESIGN — architectural contract for implementation.  
**Author/owner:** Antigravity (Gemini) designs & verifies; Big Pickle (OpenCode) implements.  
**Milestone:** Phase 4: M5 (Embodiment & External Device Nodes), package M5.2.  
**Baseline:** `task/supervisor @ 7d6c920`, **827 passed in 259.81s**, 0 failed.  
**Proof Target (M5.2):** `node pairing -> capability handshake -> authenticated RPC dispatch -> heartbeat monitor -> fail-closed disconnect`.

---

## 1. Why This Exists

JARVIS must not remain imprisoned on a single workstation process. Physical embodiment and continuous living deployment require communicating with external physical nodes:
1. **Phone Nodes (Companion Bodies)**: Mobile sensor telemetry (GPS, camera, mic) and mobile notifications.
2. **Embedded & Robotics Nodes**: Microcontrollers, Raspberry Pis, motor controllers, and robotic arms.
3. **Peripheral Sensor Hubs**: IoT environmental sensors, displays, and GPIO switches.

To preserve JARVIS's core safety invariants:
- External nodes must sit strictly behind an **External Capability Substitution Seam** (`ProviderAdapter`).
- Nodes must **never** join unauthenticated; every node requires mutual cryptographic attestation grounded in Creator authority (`new_pairing_code`).
- Communication must be lightweight (JSON-RPC / binary framing) and transport-agnostic (WebSocket, TCP, or in-memory test mocks).
- Lost connectivity must **fail closed**: a dead heartbeat immediately halts active node effects and transitions the node to `HOLD`.

---

## 2. Grounding in Existing Modules

- **`src/jarvis/bootstrap.py`**: `new_pairing_code()` defines the human-readable ambiguity-free pairing alphabet (`XXXX-XXXX`).
- **`src/jarvis/kernel/identity.py`**: Cryptographic identity, signing keys, and signature verification.
- **`src/jarvis/orchestrator/bridges/protocol.py`**: Sandbox and handle contracts.
- **`src/jarvis/kernel/manifest_dag.py`**: Resource locking and execution waves.

---

## 3. Detailed Design Contract

### A. Data Structures (`src/jarvis/nodes/protocol.py`)

```python
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

class NodeType(str, enum.Enum):
    WORKSTATION = "workstation"
    PHONE = "phone"
    EMBEDDED_ROBOT = "embedded_robot"
    IOT_PERIPHERAL = "iot_peripheral"
    SENSOR_NODE = "sensor_node"

class PairingState(str, enum.Enum):
    UNPAIRED = "unpaired"
    PENDING = "pending"
    PAIRED = "paired"
    REVOKED = "revoked"
    EXPIRED = "expired"

@dataclass(frozen=True)
class NodeCapability:
    name: str
    version: str
    description: str = ""
    required_permissions: tuple[str, ...] = ()
    effect_types: tuple[str, ...] = ()

@dataclass(frozen=True)
class NodeSpec:
    node_id: str
    name: str
    node_type: NodeType
    capabilities: tuple[NodeCapability, ...]
    public_key: str
    paired_at: str = ""
    last_seen: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class PairingRequest:
    node_id: str
    name: str
    node_type: NodeType
    capabilities: tuple[NodeCapability, ...]
    public_key: str
    pairing_code: str
    timestamp: str

@dataclass(frozen=True)
class PairingResponse:
    success: bool
    node_id: str
    state: PairingState
    session_token: str = ""
    error_message: str = ""

@dataclass(frozen=True)
class RPCRequest:
    request_id: str
    method: str
    params: Mapping[str, Any] = field(default_factory=dict)
    node_id: str = ""
    timestamp: str = ""
    signature: str = ""

@dataclass(frozen=True)
class RPCResponse:
    request_id: str
    success: bool
    result: Any = None
    error_code: int = 0
    error_message: str = ""

@dataclass(frozen=True)
class HeartbeatPacket:
    node_id: str
    sequence: int
    timestamp: str
    status: str = "ok"
```

### B. Transport Seam & Node Manager (`src/jarvis/nodes/rpc_adapter.py`)

1. **`NodeTransport` Protocol**:
   - `send(node_id: str, payload: str) -> None`
   - `receive(timeout: float | None = None) -> tuple[str, str] | None` (returns `(node_id, payload)`)
   - `is_connected(node_id: str) -> bool`

2. **`NodeManager`**:
   - `register_pairing_code(code: str, ttl_seconds: float = 300.0) -> None`
   - `handle_pairing_request(req: PairingRequest) -> PairingResponse`
   - `dispatch_rpc(node_id: str, method: str, params: Mapping[str, Any], timeout: float = 10.0) -> RPCResponse`
   - `record_heartbeat(hb: HeartbeatPacket) -> bool`
   - `check_heartbeat_timeouts(timeout_seconds: float = 15.0) -> tuple[str, ...]` (returns IDs of timed-out nodes, transitions them to `HOLD`)

---

## 4. Test Suite Requirements (`tests/nodes/test_node_rpc.py`)

1. **`test_pairing_success_with_valid_code`**: Node presents valid pairing code -> state PAIRED.
2. **`test_pairing_rejected_with_invalid_code`**: Node presents wrong code -> state UNPAIRED/REJECTED.
3. **`test_pairing_rejected_when_code_expired`**: Expired TTL rejects pairing request.
4. **`test_rpc_dispatch_and_response_roundtrip`**: In-memory transport roundtrips request/response matching `request_id`.
5. **`test_rpc_unknown_node_raises_or_fails`**: Calling RPC on unregistered node returns fail-closed error.
6. **`test_heartbeat_updates_last_seen`**: Successive heartbeats update timestamps without latency accumulation.
7. **`test_heartbeat_timeout_transitions_to_hold`**: Missed heartbeats (>15s) detect node disconnection and revoke active execution.
8. **`test_capability_filtering`**: Invoking an RPC method not declared in `NodeCapability` is rejected fail-closed before transmission.

---

## 5. Work Division (Pair-Programming Pipeline)

1. **Antigravity (Chief Architect)**:
   - Publishes and commits `docs/M5_2_KICKOFF.md`.
   - Creates package scaffolding (`src/jarvis/nodes/`).
2. **OpenCode (Hands-on Builder)**:
   - Headlessly implement `src/jarvis/nodes/protocol.py`.
   - Headlessly implement `src/jarvis/nodes/rpc_adapter.py`.
   - Headlessly implement `tests/nodes/test_node_rpc.py`.
3. **Antigravity (Quality Reviewer & Verifier)**:
   - Audits code quality, executes test suite (`uv run pytest tests/nodes/`), verifies 0 regressions across all 827 baseline tests.
   - Commits M5.2 to `task/supervisor`.
