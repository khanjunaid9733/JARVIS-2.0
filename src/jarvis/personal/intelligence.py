"""Personal Intelligence Engine for JARVIS.

Bridges persistent creator knowledge, autobiographical memory,
situational awareness, and conversational persona into a unified personal AI.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

from .persona import JarvisPersona
from .profile import PersonalProfileManager, UserProfile, get_profile_manager

logger = logging.getLogger("jarvis.personal.intelligence")


class PersonalIntelligenceEngine:
    """Orchestrates personal intelligence, autobiographical learning, and persona calibration."""

    def __init__(
        self,
        profile_manager: Optional[PersonalProfileManager] = None,
        persona: Optional[type[JarvisPersona]] = None,
    ) -> None:
        self.profile_manager = profile_manager or get_profile_manager()
        self.persona = persona or JarvisPersona

    @property
    def profile(self) -> UserProfile:
        return self.profile_manager.profile

    def process_user_turn_for_learning(self, user_text: str) -> Optional[str]:
        """Extract biographical facts, preferences, and personal context dynamically."""
        text = user_text.strip()
        lowered = text.lower()

        # 1. Identity / Name declaration ("call me X", "my name is X")
        name_match = re.search(r"\b(?:call\s+me|my\s+name\s+is)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)", text, re.IGNORECASE)
        if name_match:
            new_name = name_match.group(1).strip().title()
            if len(new_name) >= 2 and new_name.lower() not in ("sir", "jarvis", "mr", "boss"):
                self.profile.name = new_name
                self.profile_manager.save()
                return f"I shall remember your name as {new_name}, sir."

        # 2. Preference learning ("I like/love/prefer X", "my favorite X is Y")
        pref_match = re.search(r"\b(?:i\s+(?:really\s+)?(?:like|love|prefer|enjoy)|my\s+favorite\s+\w+\s+is)\s+([^.!?,\n]{4,60})", text, re.IGNORECASE)
        if pref_match:
            fact = f"User preference: enjoys {pref_match.group(1).strip()}"
            if self.profile_manager.learn_fact(fact):
                return f"Noted in your personal profile: {fact}, sir."

        # 3. Active project learning ("I am working on X", "building X")
        proj_match = re.search(r"\b(?:i\s+am\s+(?:currently\s+)?(?:working\s+on|building|coding|developing))\s+([^.!?,\n]{4,60})", text, re.IGNORECASE)
        if proj_match:
            proj = proj_match.group(1).strip()
            if self.profile_manager.add_project(proj):
                return f"Added '{proj}' to your active endeavors, sir."

        # 4. State of mind / Fatigue ("I'm tired", "I'm exhausted")
        if any(w in lowered for w in ["i'm tired", "i am tired", "exhausted", "sleepy", "need sleep"]):
            self.profile.habits["current_fatigue"] = True
            self.profile_manager.save()
            late_nudge = self.persona.get_late_night_nudge()
            if late_nudge:
                return late_nudge
            return "Do take care, sir. Even brilliant minds require regeneration."

        return None

    def get_greeting(self) -> str:
        """Get a personalized, time-grounded greeting for the Creator."""
        return self.persona.get_greeting(creator_name=self.profile.name)

    def build_system_context(self) -> str:
        """Build the complete system prompt block injecting personal intelligence into LLM calls."""
        summary = self.profile_manager.get_context_summary()
        return self.persona.get_system_prompt_directives(summary)

    def enrich_response(self, action: str, raw_reply: str) -> str:
        """Apply the authentic Bettany tone to any raw output."""
        return self.persona.polish_action_reply(action, raw_reply)


_DEFAULT_ENGINE: Optional[PersonalIntelligenceEngine] = None


def get_personal_intelligence() -> PersonalIntelligenceEngine:
    """Singleton getter for the Personal Intelligence engine."""
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = PersonalIntelligenceEngine()
    return _DEFAULT_ENGINE
