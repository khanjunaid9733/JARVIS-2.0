---
name: n8n-workflow-automation
description: Orchestrates workflow automation, webhook execution, and dynamic pipeline generation using n8n for any external service integration (Spotify, Slack, Telegram, Gmail, Home Assistant, databases, and custom APIs).
---

# n8n Workflow Automation Skill

## Purpose
Enables JARVIS to dynamically execute, create, and manage automation workflows using an n8n instance. With n8n, JARVIS can fulfill user demands across 400+ connected services and native webhooks without writing custom provider code for each third-party platform.

## When to Activate
Activate this skill whenever the user asks to:
- Connect, automate, or trigger tasks in external services (Spotify, Telegram, Discord, Google Workspace, GitHub, Slack, Notion, Home Assistant).
- Create or deploy new multi-step automation workflows on demand.
- Trigger webhooks to execute background pipelines.
- Inspect execution status or logs of automated workflows.

## Environment & Configuration
The n8n adapter reads standard environment variables:
- `N8N_BASE_URL`: Base URL of the n8n instance (e.g. `http://localhost:5678` or cloud instance).
- `N8N_API_KEY`: n8n REST API key for managing workflows and executions.
*(When unset, the adapter operates in deterministic mock mode for local testing).*

## Core Workflows

### 1. Triggering an Existing n8n Workflow via Webhook
To trigger a workflow immediately:
- Identify the target webhook endpoint name (e.g. `spotify-play`, `discord-alert`, `backup-trigger`).
- Prepare the JSON payload according to the workflow schema.
- Invoke the contract:
  ```python
  from jarvis.adapters.n8n import N8nWorkflowAdapter

  adapter = N8nWorkflowAdapter()
  result = await adapter.invoke(
      contract_id="n8n.webhook.trigger",
      version="1.0.0",
      args={
          "endpoint": "spotify-play",
          "payload": {"action": "play", "query": "Lofi Beats"},
          "method": "POST",
      },
  )
  ```

### 2. Dynamically Creating a New n8n Workflow
When a user requests a workflow that does not exist yet:
1. Define the workflow graph (Nodes + Connections):
   - **Trigger Node**: e.g., `n8n-nodes-base.webhook` or `n8n-nodes-base.scheduleTrigger`.
   - **Action Nodes**: e.g., `n8n-nodes-base.httpRequest`, `n8n-nodes-base.spotify`, `n8n-nodes-base.telegram`.
2. Post to the n8n workflow creation API:
   ```python
   result = await adapter.invoke(
       contract_id="n8n.workflow.create",
       version="1.0.0",
       args={
           "name": "Auto User Notification",
           "nodes": [
               {
                   "name": "Webhook",
                   "type": "n8n-nodes-base.webhook",
                   "typeVersion": 1,
                   "position": [250, 300],
                   "parameters": {"path": "notify-user", "httpMethod": "POST"},
               },
               {
                   "name": "Send Alert",
                   "type": "n8n-nodes-base.httpRequest",
                   "typeVersion": 1,
                   "position": [450, 300],
                   "parameters": {"url": "https://api.service.com/notify", "method": "POST"},
               },
           ],
           "connections": {
               "Webhook": {
                   "main": [[{"node": "Send Alert", "type": "main", "index": 0}]]
               }
           },
       },
   )
   ```
3. Activate the workflow:
   ```python
   await adapter.invoke(
       contract_id="n8n.workflow.activate",
       version="1.0.0",
       args={"workflow_id": result["id"], "active": True},
   )
   ```

### 3. Monitoring & Validating Executions
Query execution outcomes to verify delivery:
```python
exec_data = await adapter.invoke(
    contract_id="n8n.execution.get",
    version="1.0.0",
    args={"execution_id": execution_id},
)
```

## Best Practices & Safety Invariants
- **Deterministic Seams**: Always route through `N8nWorkflowAdapter`; do not embed ad-hoc `requests` or `curl` calls directly in kernel logic.
- **Fail-Closed**: If the n8n endpoint is unreachable or returns a non-200 status, gracefully handle the error and report the exact failure code.
- **Privacy & Token Security**: Never log raw API secrets or credentials into the unencrypted event log.
