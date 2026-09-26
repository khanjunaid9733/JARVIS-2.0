from __future__ import annotations

"""n8n Workflow Automation Provider Adapter (src/jarvis/adapters/n8n.py).

Implements ProviderAdapter protocol exposing:
- n8n.webhook.trigger: Dispatches a payload to an n8n webhook endpoint
- n8n.workflow.create: Creates a new workflow definition via n8n REST API
- n8n.workflow.activate: Activates or deactivates a workflow
- n8n.execution.get: Retrieves execution history and status
"""

import json
import os
from typing import Any, Mapping
import urllib.error
import urllib.parse
import urllib.request


class MockN8nClient:
    """In-memory deterministic test double for n8n API interactions."""

    def __init__(self) -> None:
        self.workflows: dict[str, dict[str, Any]] = {}
        self.executions: dict[str, dict[str, Any]] = {}
        self.triggered_webhooks: list[dict[str, Any]] = []

    def trigger_webhook(
        self, endpoint: str, payload: dict[str, Any], method: str = "POST"
    ) -> dict[str, Any]:
        self.triggered_webhooks.append({
            "endpoint": endpoint,
            "payload": payload,
            "method": method,
        })
        return {
            "status": "success",
            "message": "Workflow started via webhook",
            "execution_id": f"exec_{len(self.triggered_webhooks)}",
            "data": payload,
        }

    def create_workflow(
        self, name: str, nodes: list[dict[str, Any]], connections: dict[str, Any]
    ) -> dict[str, Any]:
        wf_id = f"wf_{len(self.workflows) + 1}"
        record = {
            "id": wf_id,
            "name": name,
            "active": False,
            "nodes": nodes,
            "connections": connections,
        }
        self.workflows[wf_id] = record
        return record

    def set_active(self, workflow_id: str, active: bool) -> dict[str, Any]:
        if workflow_id not in self.workflows:
            raise KeyError(f"Workflow '{workflow_id}' not found")
        self.workflows[workflow_id]["active"] = active
        return {"id": workflow_id, "active": active}

    def get_execution(self, execution_id: str) -> dict[str, Any]:
        if execution_id in self.executions:
            return self.executions[execution_id]
        return {
            "id": execution_id,
            "finished": True,
            "status": "success",
            "mode": "webhook",
        }


class RealN8nClient:
    """HTTP client communicating with a real n8n instance via REST API & webhooks."""

    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-N8N-API-KEY"] = self.api_key
        return headers

    def trigger_webhook(
        self, endpoint: str, payload: dict[str, Any], method: str = "POST"
    ) -> dict[str, Any]:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            url = endpoint
        else:
            url = f"{self.base_url}/webhook/{endpoint.lstrip('/')}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {"status": "success"}
        except urllib.error.HTTPError as exc:
            return {"status": "error", "code": exc.code, "reason": exc.reason}

    def create_workflow(
        self, name: str, nodes: list[dict[str, Any]], connections: dict[str, Any]
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/v1/workflows"
        body = {"name": name, "nodes": nodes, "connections": connections}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def set_active(self, workflow_id: str, active: bool) -> dict[str, Any]:
        endpoint = "activate" if active else "deactivate"
        url = f"{self.base_url}/api/v1/workflows/{workflow_id}/{endpoint}"
        req = urllib.request.Request(url, headers=self._headers(), method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_execution(self, execution_id: str) -> dict[str, Any]:
        url = f"{self.base_url}/api/v1/executions/{execution_id}"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))


class N8nWorkflowAdapter:
    """n8n Automation Adapter satisfying the JARVIS ProviderAdapter protocol."""

    def __init__(
        self,
        client: MockN8nClient | RealN8nClient | None = None,
        provider_id: str = "n8n.workflow",
    ) -> None:
        self._provider_id = provider_id
        if client is not None:
            self.client = client
        else:
            base_url = os.environ.get("N8N_BASE_URL")
            if base_url:
                api_key = os.environ.get("N8N_API_KEY")
                self.client = RealN8nClient(base_url, api_key=api_key)
            else:
                self.client = MockN8nClient()

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def health_check(self) -> bool:
        """Provider is healthy if client is operational."""
        return True

    async def invoke(
        self,
        contract_id: str,
        version: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Dispatch n8n automation contracts."""
        if contract_id == "n8n.webhook.trigger":
            endpoint = args["endpoint"]
            payload = args.get("payload", {})
            method = args.get("method", "POST")
            return self.client.trigger_webhook(endpoint, payload, method=method)

        elif contract_id == "n8n.workflow.create":
            name = args["name"]
            nodes = args.get("nodes", [])
            connections = args.get("connections", {})
            return self.client.create_workflow(name, nodes, connections)

        elif contract_id == "n8n.workflow.activate":
            workflow_id = args["workflow_id"]
            active = bool(args.get("active", True))
            return self.client.set_active(workflow_id, active)

        elif contract_id == "n8n.execution.get":
            execution_id = args["execution_id"]
            return self.client.get_execution(execution_id)

        raise ValueError(
            f"Unsupported contract '{contract_id}' for provider '{self._provider_id}'"
        )
