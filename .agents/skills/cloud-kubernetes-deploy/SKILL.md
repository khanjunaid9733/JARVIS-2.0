---
name: cloud-kubernetes-deploy
description: Apply manifests and check pod status in a Kubernetes cluster.
---

# Kubernetes Deployment Skill

## Purpose
Apply manifests and check pod status in a Kubernetes cluster.

## When to Activate
Activate when the user asks to:
- deploy to Kubernetes
- kubectl apply
- k8s deploy

## Core Workflows

```bash
kubectl apply -f manifest.yaml
kubectl get pods -n <namespace>
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
