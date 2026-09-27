"""Persistent Creator & Personal Intelligence Profile.

Maintains the long-term identity, habits, preferences, and autobiographical
knowledge of JARVIS's Creator (Junaid Khan / sir).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("jarvis.personal.profile")


@dataclass
class UserProfile:
    """Structured representation of the Creator's personal intelligence profile."""

    name: str = "Junaid Khan"
    callsign: str = "sir"
    location: str = "Kolkata, West Bengal, India"
    timezone: str = "Asia/Kolkata"
    active_projects: list[str] = field(
        default_factory=lambda: ["JARVIS 2.0 Autonomous Cognitive OS"]
    )
    interests: list[str] = field(
        default_factory=lambda: [
            "Autonomous Agents",
            "Cognitive Architectures",
            "Systems Programming",
            "Robotics & Spatial Computing",
            "High-Performance Python",
        ]
    )
    habits: dict[str, Any] = field(
        default_factory=lambda: {
            "night_owl": True,
            "prefers_concise": True,
            "tone_style": "witty_british",
            "auto_confirm_safe_actions": True,
        }
    )
    facts: list[str] = field(
        default_factory=lambda: [
            "Creator and Chief Architect of the JARVIS 2.0 system.",
            "Operates on a Windows workstation with PowerShell and VS Code.",
            "Values deterministic execution, verified code, and elegant design.",
            "Prefers British cadence and dry, intellectual humor in dialogue.",
        ]
    )
    last_active_timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserProfile":
        valid_keys = {
            "name",
            "callsign",
            "location",
            "timezone",
            "active_projects",
            "interests",
            "habits",
            "facts",
            "last_active_timestamp",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class PersonalProfileManager:
    """Manages reading, caching, learning, and persisting the Creator Profile."""

    DEFAULT_DIR = Path.home() / ".jarvis"
    PROFILE_FILENAME = "creator_profile.json"

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        event_sink: Optional[Any] = None,
    ) -> None:
        self.storage_path = (
            storage_path or (self.DEFAULT_DIR / self.PROFILE_FILENAME)
        )
        self.event_sink = event_sink
        self.profile = self._load()

    def _auto_discover_name(self) -> str:
        """Attempt to read author name from Windows environment or git config."""
        win_user = os.environ.get("USERNAME", "")
        if "khan" in win_user.lower() or "junaid" in win_user.lower():
            return "Junaid Khan"

        try:
            res = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                timeout=1.5,
            )
            if res.returncode == 0 and res.stdout.strip():
                val = res.stdout.strip()
                if "jarvis" not in val.lower() and "bot" not in val.lower():
                    return val
        except Exception:
            pass

        return "Junaid Khan"

    def _load(self) -> UserProfile:
        """Load user profile from disk or instantiate default."""
        if self.storage_path.exists():
            try:
                content = self.storage_path.read_text(encoding="utf-8")
                data = json.loads(content)
                profile = UserProfile.from_dict(data)
                profile.last_active_timestamp = time.time()
                return profile
            except Exception as exc:
                logger.warning("Failed to load user profile: %s. Using default.", exc)

        default_name = self._auto_discover_name()
        profile = UserProfile(name=default_name)
        self.save(profile)
        return profile

    def save(self, profile: Optional[UserProfile] = None) -> None:
        """Persist current user profile to disk atomically."""
        if profile is not None:
            self.profile = profile

        self.profile.last_active_timestamp = time.time()
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.storage_path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(self.profile.to_dict(), indent=2),
                encoding="utf-8",
            )
            temp_path.replace(self.storage_path)

            if self.event_sink:
                try:
                    self.event_sink.audit(
                        stream_id="personal_profile",
                        event_type="profile.updated",
                        principal_id="personal_intelligence",
                        payload={"name": self.profile.name, "facts_count": len(self.profile.facts)},
                    )
                except Exception:
                    pass
        except Exception as exc:
            logger.error("Failed to save creator profile: %s", exc)

    def learn_fact(self, fact: str) -> bool:
        """Add a learned biographical fact to the profile if not already present."""
        cleaned = fact.strip().rstrip(".") + "."
        if not cleaned or len(cleaned) < 5:
            return False

        lowered_facts = [f.lower() for f in self.profile.facts]
        if cleaned.lower() not in lowered_facts:
            self.profile.facts.append(cleaned)
            self.save()
            return True
        return False

    def update_preference(self, key: str, value: Any) -> None:
        """Update a creator preference."""
        self.profile.habits[key] = value
        self.save()

    def add_project(self, project_name: str) -> bool:
        """Register an active project."""
        p_clean = project_name.strip()
        if p_clean and p_clean not in self.profile.active_projects:
            self.profile.active_projects.append(p_clean)
            self.save()
            return True
        return False

    def get_context_summary(self) -> str:
        """Format a concise contextual summary of the creator for LLM system prompt injection."""
        p = self.profile
        facts_bullet = "\n".join(f"- {f}" for f in p.facts[-8:])
        projects_str = ", ".join(p.active_projects)
        return (
            f"Creator Identity: {p.name} (addressed as '{p.callsign}')\n"
            f"Timezone & Base: {p.timezone} ({p.location})\n"
            f"Active Endeavors: {projects_str}\n"
            f"Biographical & Contextual Memory:\n"
            f"{facts_bullet}"
        )


_DEFAULT_MANAGER: Optional[PersonalProfileManager] = None


def get_profile_manager() -> PersonalProfileManager:
    """Singleton getter for the persistent profile manager."""
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is None:
        _DEFAULT_MANAGER = PersonalProfileManager()
    return _DEFAULT_MANAGER
