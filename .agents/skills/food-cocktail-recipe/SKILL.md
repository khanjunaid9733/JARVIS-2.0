---
name: food-cocktail-recipe
description: Find and explain cocktail recipes with techniques.
---

# Cocktail Recipe Finder Skill

## Purpose
Find and explain cocktail recipes with techniques.

## When to Activate
Activate when the user asks to:
- cocktail recipe
- how to make
- drink recipe
- bartender guide

## Core Workflows

Prompt: `Provide the recipe for {cocktail} including: ingredients, measurements, technique, glassware, garnish.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
