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
