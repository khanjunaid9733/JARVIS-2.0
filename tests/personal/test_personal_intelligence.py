from __future__ import annotations

"""Unit and Integration Tests for JARVIS Personality & Personal Intelligence Engine."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jarvis.personal.intelligence import PersonalIntelligenceEngine
from jarvis.personal.persona import JarvisPersona
from jarvis.personal.profile import PersonalProfileManager, UserProfile
from jarvis.skills.cognitive_agent import CognitiveAgent


def test_user_profile_defaults_and_serialization():
    """Verify UserProfile default structure and serialization consistency."""
    profile = UserProfile()
    assert profile.name == "Junaid Khan"
    assert profile.callsign == "sir"
    assert "JARVIS 2.0 Autonomous Cognitive OS" in profile.active_projects
    assert len(profile.facts) >= 4

    p_dict = profile.to_dict()
    assert isinstance(p_dict, dict)
    assert p_dict["name"] == "Junaid Khan"

    restored = UserProfile.from_dict(p_dict)
    assert restored.name == profile.name
    assert restored.callsign == profile.callsign
    assert restored.facts == profile.facts


def test_profile_manager_persistence(tmp_path: Path):
    """Verify atomic persistence, caching, and loading of creator profile."""
    storage_file = tmp_path / "test_profile.json"
    manager = PersonalProfileManager(storage_path=storage_file)

    # Initial profile saved
    assert storage_file.exists()
    assert manager.profile.name == "Junaid Khan"

    # Learn fact
    ok = manager.learn_fact("Enjoys espresso while debugging.")
    assert ok is True
    assert "Enjoys espresso while debugging." in manager.profile.facts

    # Duplicate fact should not be added
    duplicate_ok = manager.learn_fact("Enjoys espresso while debugging.")
    assert duplicate_ok is False

    # Add project
    p_ok = manager.add_project("Quantum Simulator")
    assert p_ok is True
    assert "Quantum Simulator" in manager.profile.active_projects

    # Update preference
    manager.update_preference("theme", "deep_space")
    assert manager.profile.habits["theme"] == "deep_space"

    # Reload fresh instance from disk
    manager2 = PersonalProfileManager(storage_path=storage_file)
    assert "Enjoys espresso while debugging." in manager2.profile.facts
    assert "Quantum Simulator" in manager2.profile.active_projects
    assert manager2.profile.habits["theme"] == "deep_space"


def test_profile_manager_context_summary(tmp_path: Path):
    """Verify concise context summary generation for LLM prompt injection."""
    profile = UserProfile(name="Junaid Khan", callsign="sir")
    manager = PersonalProfileManager(storage_path=tmp_path / "summary_test.json")
    manager.profile = profile

    summary = manager.get_context_summary()
    assert "Creator Identity: Junaid Khan" in summary
    assert "Active Endeavors:" in summary
    assert "Biographical & Contextual Memory:" in summary


def test_jarvis_persona_greetings_and_wit():
    """Verify authentic Paul Bettany British persona tone across conditions."""
    # Test greetings
    greeting = JarvisPersona.get_greeting(creator_name="Junaid Khan")
    assert isinstance(greeting, str)
    assert len(greeting) > 10
    assert "sir" in greeting.lower() or "junaid" in greeting.lower() or "mr. khan" in greeting.lower()

    # Test polished action replies
    vol_up = JarvisPersona.polish_action_reply("volume_up", "Volume increased, sir.")
    assert "volume" in vol_up.lower() or "audio" in vol_up.lower() or "turned up" in vol_up.lower()

    lock_rep = JarvisPersona.polish_action_reply("lock_workstation", "Workstation locked and secured, sir.")
    assert "locked" in lock_rep.lower() or "secure" in lock_rep.lower()

    # Unknown action returns raw reply
    raw = JarvisPersona.polish_action_reply("unknown_action_xyz", "Default text.")
    assert raw == "Default text."

    # Test hardware load commentary
    wit = JarvisPersona.get_system_wit(cpu_percent=92.0, ram_percent=40.0)
    assert wit is not None
    assert "processor is breathing" in wit

    low_wit = JarvisPersona.get_system_wit(cpu_percent=20.0, ram_percent=30.0)
    assert low_wit is None


def test_personal_intelligence_engine_learning(tmp_path: Path):
    """Verify dynamic fact extraction and personal context updates."""
    storage_file = tmp_path / "engine_test_profile.json"
    mgr = PersonalProfileManager(storage_path=storage_file)
    engine = PersonalIntelligenceEngine(profile_manager=mgr)

    # 1. Learn preference
    reply = engine.process_user_turn_for_learning("I really love neural networks and quantum computing")
    assert reply is not None
    assert "Noted in your personal profile" in reply
    assert any("neural networks and quantum computing" in f.lower() for f in engine.profile.facts)

    # 2. Learn active project
    p_reply = engine.process_user_turn_for_learning("I am currently building Autonomous Satellite Mesh")
    assert p_reply is not None
    assert "Autonomous Satellite Mesh" in engine.profile.active_projects

    # 3. Detect fatigue
    fatigue_reply = engine.process_user_turn_for_learning("I'm exhausted from coding all night")
    assert fatigue_reply is not None
    assert engine.profile.habits.get("current_fatigue") is True

    # 4. Irrelevant sentence does not trigger false learning
    noop = engine.process_user_turn_for_learning("run dir on c drive")
    assert noop is None


def test_cognitive_agent_personal_intelligence_integration(tmp_path: Path):
    """Verify CognitiveAgent seamlessly handles identity, greetings, and dynamic learning."""
    storage_file = tmp_path / "agent_profile.json"
    mgr = PersonalProfileManager(storage_path=storage_file)
    engine = PersonalIntelligenceEngine(profile_manager=mgr)

    agent = CognitiveAgent(personal_intelligence=engine)

    # 1. Identity query: Who are you
    turn1 = agent.process_turn("who are you")
    assert turn1.action == "identify"
    assert "J.A.R.V.I.S." in turn1.reply
    assert "2,400" in turn1.reply

    # 2. Creator profile query: Who am I
    turn2 = agent.process_turn("who am i and what do you know about me")
    assert turn2.action == "creator_profile_recalled"
    assert "Junaid Khan" in turn2.reply
    assert "Creator and Chief Architect" in turn2.reply
    assert "Kolkata" in turn2.reply

    # 3. British Persona greeting
    turn3 = agent.process_turn("hello jarvis")
    assert turn3.action == "greeting"
    assert "sir" in turn3.reply.lower() or "diagnostics" in turn3.reply.lower() or "good" in turn3.reply.lower()

    # 4. Autobiographical preference learning
    turn4 = agent.process_turn("I prefer dark mode and high contrast visual styling")
    assert turn4.action == "personal_intelligence_learned"
    assert "Noted in your personal profile" in turn4.reply
    assert any("dark mode" in f.lower() for f in agent.personal_intelligence.profile.facts)
