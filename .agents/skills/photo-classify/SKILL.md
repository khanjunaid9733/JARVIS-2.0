---
name: photo-classify
description: Classify images into categories using a pre-trained CNN model.
---

# Image Classifier Skill

## Purpose
Classify images into categories using a pre-trained CNN model.

## When to Activate
Activate when the user asks to:
- classify image
- what is in image
- image recognition
- identify object

## Core Workflows

Use EfficientNet or MobileNet via TensorFlow/PyTorch for top-5 classification.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
