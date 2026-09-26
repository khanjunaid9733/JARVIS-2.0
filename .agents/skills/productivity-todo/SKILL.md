---
name: productivity-todo
description: Create, read, complete, and delete to-do items.
---

# To-Do List Manager Skill

## Purpose
Create, read, complete, and delete to-do items.

## When to Activate
Activate when the user asks to:
- add task
- mark as done
- my to-do list
- what do I need to do

## Core Workflows

Store tasks as JSON in JARVIS_HOME/todos.json, sync to durable memory.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
