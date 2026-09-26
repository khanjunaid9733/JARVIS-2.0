---
name: cloud-aws-lambda-invoke
description: Invoke an AWS Lambda function and return its result.
---

# AWS Lambda Invoker Skill

## Purpose
Invoke an AWS Lambda function and return its result.

## When to Activate
Activate when the user asks to:
- run Lambda
- invoke <function>
- trigger Lambda

## Core Workflows

```python
boto3.client('lambda').invoke(FunctionName=name, Payload=json.dumps(event))
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
