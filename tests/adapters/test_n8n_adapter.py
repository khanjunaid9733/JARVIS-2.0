from __future__ import annotations

"""Unit tests for n8n Workflow Automation Provider Adapter (src/jarvis/adapters/n8n.py)."""

import pytest

from jarvis.adapters.n8n import MockN8nClient, N8nWorkflowAdapter

pytestmark = pytest.mark.anyio


async def test_n8n_adapter_health_check():
    adapter = N8nWorkflowAdapter()
    assert adapter.health_check() is True
    assert adapter.provider_id == "n8n.workflow"


async def test_n8n_webhook_trigger():
    mock_client = MockN8nClient()
    adapter = N8nWorkflowAdapter(client=mock_client)

    result = await adapter.invoke(
        contract_id="n8n.webhook.trigger",
        version="1.0.0",
        args={
            "endpoint": "test-webhook",
            "payload": {"action": "play_music", "track": "Bohemian Rhapsody"},
        },
    )

    assert result["status"] == "success"
    assert result["execution_id"] == "exec_1"
    assert len(mock_client.triggered_webhooks) == 1
    assert mock_client.triggered_webhooks[0]["endpoint"] == "test-webhook"
    assert mock_client.triggered_webhooks[0]["payload"]["track"] == "Bohemian Rhapsody"


async def test_n8n_workflow_create_and_activate():
    mock_client = MockN8nClient()
    adapter = N8nWorkflowAdapter(client=mock_client)

    # 1. Create workflow
    nodes = [{"name": "Webhook", "type": "n8n-nodes-base.webhook"}]
    connections = {}
    create_result = await adapter.invoke(
        contract_id="n8n.workflow.create",
        version="1.0.0",
        args={"name": "Auto Spotify Controller", "nodes": nodes, "connections": connections},
    )

    assert create_result["id"] == "wf_1"
    assert create_result["name"] == "Auto Spotify Controller"
    assert create_result["active"] is False

    # 2. Activate workflow
    act_result = await adapter.invoke(
        contract_id="n8n.workflow.activate",
        version="1.0.0",
        args={"workflow_id": "wf_1", "active": True},
    )
    assert act_result["id"] == "wf_1"
    assert act_result["active"] is True


async def test_n8n_execution_get():
    mock_client = MockN8nClient()
    mock_client.executions["exec_100"] = {
        "id": "exec_100",
        "finished": True,
        "status": "success",
        "data": {"result": "ok"},
    }
    adapter = N8nWorkflowAdapter(client=mock_client)

    exec_result = await adapter.invoke(
        contract_id="n8n.execution.get",
        version="1.0.0",
        args={"execution_id": "exec_100"},
    )
    assert exec_result["id"] == "exec_100"
    assert exec_result["status"] == "success"


async def test_n8n_invalid_contract_rejected():
    adapter = N8nWorkflowAdapter()
    with pytest.raises(ValueError, match="Unsupported contract 'unknown.contract'"):
        await adapter.invoke(
            contract_id="unknown.contract",
            version="1.0.0",
            args={},
        )
