---
name: pm-jira-create
description: Create Jira issues, bugs, and epics via API.
---

# Jira Issue Creator Skill

## Purpose
Create Jira issues, bugs, and epics via API.

## When to Activate
Activate when the user asks to:
- create Jira issue
- log bug in Jira
- Jira ticket
- new Jira task

## Core Workflows

POST to Jira REST API `/rest/api/3/issue` with project key, issuetype, summary.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
