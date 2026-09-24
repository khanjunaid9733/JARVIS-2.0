from __future__ import annotations

import json
from pathlib import Path
import pytest

from jarvis.kernel.event_log import Event, EventIntegrityError, EventLog
from jarvis.kernel.sync.replication import (
    ReplicationConflictError,
    ReplicationEngine,
    SyncBatch,
    VectorClock,
)
from jarvis.nodes.protocol import NodeCapability, NodeSpec, NodeType, PairingRequest, RPCResponse
from jarvis.nodes.rpc_adapter import InMemoryNodeTransport, NodeManager


@pytest.fixture
def temp_logs(tmp_path: Path):
    hub_path = tmp_path / "hub_log.db"
    node_path = tmp_path / "node_log.db"
    hub_log = EventLog(db_path=hub_path)
    node_log = EventLog(db_path=node_path)
    return hub_log, node_log


def test_vector_clock_monotonicity():
    vc1 = VectorClock().increment("hub", 1).increment("node_1", 3)
    vc2 = VectorClock().increment("hub", 1).increment("node_1", 2)
    vc3 = VectorClock().increment("hub", 2).increment("node_1", 2)

    assert vc1.is_causally_newer(vc2)
    assert not vc2.is_causally_newer(vc1)
    # Concurrent / divergent clocks: neither is strictly newer
    assert not vc1.is_causally_newer(vc3)
    assert not vc3.is_causally_newer(vc1)

    merged = vc1.merge(vc3)
    assert merged.get("hub") == 2
    assert merged.get("node_1") == 3
    assert merged.is_causally_newer(vc1)
    assert merged.is_causally_newer(vc3)


def test_export_batch_filters_by_watermark(temp_logs):
    hub_log, _ = temp_logs
    engine = ReplicationEngine(hub_log, local_node_id="hub")

    # Append 5 events
    for i in range(1, 6):
        hub_log.append(
            Event(
                stream_id="hub.tasks",
                event_type="task.created",
                principal_id="creator",
                payload={"index": i},
            )
        )

    # Export all
    batch_all = engine.export_batch(target_node_id="node_1")
    assert len(batch_all.events) == 5
    assert batch_all.stream_watermarks["hub.tasks"] == 5

    # Export since sequence 3
    batch_since_3 = engine.export_batch(
        target_node_id="node_1", since_stream_seqs={"hub.tasks": 3}
    )
    assert len(batch_since_3.events) == 2
    assert [ev.payload["index"] for ev in batch_since_3.events] == [4, 5]


def test_ingest_batch_appends_cleanly(temp_logs):
    hub_log, node_log = temp_logs
    node_engine = ReplicationEngine(node_log, local_node_id="node_1")
    hub_engine = ReplicationEngine(hub_log, local_node_id="hub")

    # Node creates local telemetry events
    for i in range(1, 4):
        node_log.append(
            Event(
                stream_id="node.telemetry",
                event_type="sensor.sample",
                principal_id="node_1",
                payload={"battery": 100 - i * 5},
            )
        )

    batch = node_engine.export_batch(target_node_id="hub")
    summary = hub_engine.ingest_batch(batch)

    assert summary.applied_count == 3
    assert summary.skipped_count == 0
    assert len(summary.conflicts) == 0

    # Hub's event log now has 3 events and a valid cryptographic chain
    cur = hub_log._conn.execute("SELECT COUNT(*) AS c FROM events")
    assert cur.fetchone()["c"] == 3
    assert hub_log.verify_chain()


def test_ingest_batch_is_idempotent(temp_logs):
    hub_log, node_log = temp_logs
    node_engine = ReplicationEngine(node_log, local_node_id="node_1")
    hub_engine = ReplicationEngine(hub_log, local_node_id="hub")

    node_log.append(
        Event(
            stream_id="node.telemetry",
            event_type="sensor.sample",
            principal_id="node_1",
            payload={"temperature": 21.5},
        )
    )

    batch = node_engine.export_batch(target_node_id="hub")
    summary_1 = hub_engine.ingest_batch(batch)
    assert summary_1.applied_count == 1
    assert summary_1.skipped_count == 0

    # Re-ingest the exact same batch
    summary_2 = hub_engine.ingest_batch(batch)
    assert summary_2.applied_count == 0
    assert summary_2.skipped_count == 1
    assert hub_log.verify_chain()


def test_tampered_payload_in_batch_raises_integrity_error(temp_logs):
    hub_log, node_log = temp_logs
    node_engine = ReplicationEngine(node_log, local_node_id="node_1")
    hub_engine = ReplicationEngine(hub_log, local_node_id="hub")

    node_log.append(
        Event(
            stream_id="node.telemetry",
            event_type="sensor.sample",
            principal_id="node_1",
            payload={"val": 42},
        )
    )

    batch = node_engine.export_batch(target_node_id="hub")
    # Tamper with event payload in flight without recomputing payload_sha256
    tampered_ev = batch.events[0].model_copy(update={"payload": {"val": 9999}})
    tampered_batch = SyncBatch(
        batch_id=batch.batch_id,
        source_node_id=batch.source_node_id,
        target_node_id=batch.target_node_id,
        events=(tampered_ev,),
        vector_clock=batch.vector_clock,
    )

    with pytest.raises(EventIntegrityError):
        hub_engine.ingest_batch(tampered_batch)


def test_conflicting_event_id_raises_replication_conflict_error(temp_logs):
    hub_log, _ = temp_logs
    hub_engine = ReplicationEngine(hub_log, local_node_id="hub")

    ev_id = "01HW1234567890ABCDEFGHJKMN"
    # Hub already committed an event with ID ev_id
    hub_log.append(
        Event(
            event_id=ev_id,
            stream_id="mission.audit",
            event_type="audit.step",
            principal_id="creator",
            payload={"step": "authorized"},
        )
    )

    # Incoming foreign batch contains identical event_id but DIFFERENT payload
    conflicting_ev = Event(
        event_id=ev_id,
        stream_id="mission.audit",
        event_type="audit.step",
        principal_id="rogue_node",
        payload={"step": "forged_malicious_step"},
    )
    conflicting_ev = conflicting_ev.model_copy(
        update={"payload_sha256": conflicting_ev.compute_payload_sha256()}
    )

    batch = SyncBatch(
        batch_id="batch_conflict",
        source_node_id="rogue_node",
        target_node_id="hub",
        events=(conflicting_ev,),
        vector_clock=VectorClock(),
    )

    # Fail closed per Invariant I6: never mutate or overwrite
    with pytest.raises(ReplicationConflictError):
        hub_engine.ingest_batch(batch)


def test_bidirectional_sync_reaches_consensus(temp_logs):
    hub_log, node_log = temp_logs
    hub_engine = ReplicationEngine(hub_log, local_node_id="hub")
    node_engine = ReplicationEngine(node_log, local_node_id="node_1")

    # Hub has mission events
    hub_log.append(
        Event(
            stream_id="mission",
            event_type="mission.planned",
            principal_id="creator",
            payload={"goal": "inspect perimeter"},
        )
    )
    # Node has sensor events
    node_log.append(
        Event(
            stream_id="telemetry",
            event_type="status.heartbeat",
            principal_id="node_1",
            payload={"gps": {"lat": 37.77, "lon": -122.41}},
        )
    )

    # Round 1: Node pushes to Hub
    batch_n2h = node_engine.export_batch(target_node_id="hub")
    hub_engine.ingest_batch(batch_n2h)

    # Round 2: Hub pushes to Node
    batch_h2n = hub_engine.export_batch(target_node_id="node_1")
    node_engine.ingest_batch(batch_h2n)

    # Both logs now have 2 events and valid chains
    assert hub_log._conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"] == 2
    assert node_log._conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"] == 2
    assert hub_log.verify_chain()
    assert node_log.verify_chain()


def test_rpc_sync_roundtrip(temp_logs):
    hub_log, node_log = temp_logs
    hub_engine = ReplicationEngine(hub_log, local_node_id="hub")
    node_engine = ReplicationEngine(node_log, local_node_id="node_phone")

    # Add telemetry to phone node
    node_log.append(
        Event(
            stream_id="phone.battery",
            event_type="battery.drain",
            principal_id="node_phone",
            payload={"level": 88},
        )
    )

    transport = InMemoryNodeTransport()
    manager = NodeManager(transport=transport)
    code = "ABCD-EFGH"
    manager.register_pairing_code(code)
    pairing_req = PairingRequest(
        node_id="node_phone",
        name="Companion Phone",
        node_type=NodeType.PHONE,
        capabilities=(
            NodeCapability(name="sync.pull_batch", version="1.0.0"),
            NodeCapability(name="sync.push_batch", version="1.0.0"),
        ),
        public_key="test_pk",
        pairing_code=code,
        timestamp="2026-09-24T20:00:00Z",
    )
    pairing_resp = manager.handle_pairing_request(pairing_req)
    assert pairing_resp.success

    # Remote node registers mock handler that returns export_batch
    def handle_pull(req_params):
        target = req_params.get("target_node_id", "hub")
        batch = node_engine.export_batch(target_node_id=target)
        return {
            "batch_id": batch.batch_id,
            "source_node_id": batch.source_node_id,
            "target_node_id": batch.target_node_id,
            "events": [ev.model_dump() for ev in batch.events],
            "vector_clock": dict(batch.vector_clock.clock),
            "stream_watermarks": dict(batch.stream_watermarks),
        }

    # Simulate RPC dispatch over NodeManager
    raw_batch_data = handle_pull({"target_node_id": "hub"})
    reconstructed_batch = SyncBatch(
        batch_id=raw_batch_data["batch_id"],
        source_node_id=raw_batch_data["source_node_id"],
        target_node_id=raw_batch_data["target_node_id"],
        events=tuple(Event(**ev) for ev in raw_batch_data["events"]),
        vector_clock=VectorClock(clock=raw_batch_data["vector_clock"]),
        stream_watermarks=raw_batch_data["stream_watermarks"],
    )

    summary = hub_engine.ingest_batch(reconstructed_batch)
    assert summary.applied_count == 1
    assert hub_log.verify_chain()
