"""ADR-011 S4: execution admission for the skill library.

Discovery and execution are separate powers. Every skill in
`.agents/skills` stays searchable, listable and inspectable; only a skill whose
id is on the execution allowlist may actually run. Admission is recorded so a
refusal is auditable rather than silent.
"""

from __future__ import annotations

import json
import os
import hashlib
from dataclasses import dataclass
from pathlib import Path

ADMISSION_FILENAME = "skill_admission.json"
DEFAULT_SKILLS_DIR = Path(".agents") / "skills"


@dataclass(frozen=True)
class AdmissionEntry:
    """One explicitly reviewed skill."""

    skill_id: str
    #: What the operator believed this skill does, recorded so a later reader
    #: can tell a reviewed entry from an accidental one.
    note: str = ""
    #: Optional expected sha256 of the SKILL.md, to pin content after review.
    source_sha256: str | None = None

    def describe(self) -> str:
        return self.note or "(no note recorded)"


@dataclass(frozen=True)
class SkillAdmissionPolicy:
    """Default-deny execution allowlist (ADR-011 S4).

    Entries are retained, not just ids, so an entry's `source_sha256` pin can
    actually be enforced. See `check_content`.
    """

    entries: frozenset[AdmissionEntry] = frozenset()

    def __post_init__(self) -> None:
        # Accept plain id strings so callers (and existing tests) can write
        # `entries=frozenset({"skill-a"})` without constructing entries. Ids
        # given this way carry no content pin.
        if any(not isinstance(e, AdmissionEntry) for e in self.entries):
            coerced: set[AdmissionEntry] = set()
            for item in self.entries:
                if isinstance(item, AdmissionEntry):
                    coerced.add(item)
                elif isinstance(item, str):
                    coerced.add(AdmissionEntry(skill_id=item))
                else:
                    raise TypeError(
                        f"admission entries must be AdmissionEntry or str, "
                        f"got {type(item).__name__}"
                    )
            object.__setattr__(self, "entries", frozenset(coerced))

    def is_admitted(self, skill_id: str) -> bool:
        return self.entry_for(skill_id) is not None

    def entry_for(self, skill_id: str) -> AdmissionEntry | None:
        for entry in self.entries:
            if entry.skill_id == skill_id:
                return entry
        return None

    def check_content(self, skill_id: str, source_path: Path | str | None) -> str | None:
        """Return a refusal reason if the on-disk content no longer matches its pin.

        Admission is by id, but the agent can rewrite any file on disk, so an
        id-only allowlist is revocable the moment a skill is admitted. An entry
        that carries a `source_sha256` is a promise that the reviewed bytes are
        the bytes that run. This enforces it.

        An entry with no pin is unpinned content and is allowed; `jarvis skill
        admit` always records a digest, so pinned is the normal case.

        Returns None when acceptable, otherwise a human-readable reason.
        """
        entry = self.entry_for(skill_id)
        if entry is None or not entry.source_sha256:
            return None
        if source_path is None:
            return (
                f"skill '{skill_id}' is admitted with a pinned sha256 but has no "
                f"readable source file to verify against"
            )
        path = Path(source_path)
        if not path.is_file():
            return (
                f"skill '{skill_id}' is admitted with a pinned sha256 but its "
                f"source file is missing: {path}"
            )
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            return f"skill '{skill_id}' source file could not be read: {exc}"
        if actual != entry.source_sha256:
            return (
                f"skill '{skill_id}' content changed after admission "
                f"(expected {entry.source_sha256[:12]}..., found {actual[:12]}...); "
                f"re-review and re-admit with `jarvis skill admit {skill_id}`"
            )
        return None

    def admitted_ids(self) -> tuple[str, ...]:
        return tuple(sorted(e.skill_id for e in self.entries))


#: Seeded from the skills that were written and reviewed by hand and that the
#: live path actually exercises. Everything else in the library stays
#: discoverable but non-executable until an operator admits it.
DEFAULT_ADMITTED: tuple[AdmissionEntry, ...] = (
    AdmissionEntry(
        skill_id="files-hash",
        note="Local file hashing; pure read + hashlib, no network, no writes.",
    ),
    AdmissionEntry(
        skill_id="security-hash-text",
        note="Local text hashing; pure read + hashlib, no network, no writes.",
    ),
)

DEFAULT_ENV_VAR = "JARVIS_SKILL_ADMISSION"


def admission_path(skills_dir: Path | str | None = None) -> Path:
    root = Path(skills_dir) if skills_dir is not None else DEFAULT_SKILLS_DIR
    return root / ADMISSION_FILENAME


def load_admission_file(path: Path | str | None = None) -> list[AdmissionEntry]:
    """Read the on-disk allowlist.

    A missing or malformed file yields an EMPTY allowlist. That is deliberate:
    an unreadable policy must deny, not fall open.
    """
    target = Path(path) if path is not None else admission_path()
    if not target.is_file():
        return []
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, dict):
        return []
    listed = raw.get("admitted")
    if not isinstance(listed, list):
        return []

    entries: list[AdmissionEntry] = []
    for item in listed:
        if isinstance(item, str):
            entries.append(AdmissionEntry(skill_id=item))
        elif isinstance(item, dict) and isinstance(item.get("skill_id"), str):
            entries.append(
                AdmissionEntry(
                    skill_id=item["skill_id"],
                    note=str(item.get("note", "")),
                    source_sha256=item.get("source_sha256"),
                )
            )
    return entries


def load_policy(
    path: Path | str | None = None,
    *,
    env: dict[str, str] | None = None,
) -> SkillAdmissionPolicy:
    """Resolve the effective policy: defaults, then file, then env override.

    Precedence, lowest to highest:
      1. `DEFAULT_ADMITTED`
      2. the `skill_admission.json` beside the skills
      3. `JARVIS_SKILL_ADMISSION` (comma-separated ids, additive)
    """
    environ = os.environ if env is None else env
    entries: dict[str, AdmissionEntry] = {e.skill_id: e for e in DEFAULT_ADMITTED}
    for entry in load_admission_file(path):
        entries[entry.skill_id] = entry

    override = environ.get(DEFAULT_ENV_VAR, "")
    if override.strip():
        for part in override.split(","):
            skill_id = part.strip()
            if skill_id:
                # An env-admitted id has no file to pin, so it stays unpinned.
                entries.setdefault(skill_id, AdmissionEntry(skill_id=skill_id))

    return SkillAdmissionPolicy(entries=frozenset(entries.values()))


def write_admission_file(
    entries: list[AdmissionEntry], path: Path | str | None = None
) -> Path:
    target = Path(path) if path is not None else admission_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "schema": 1,
                "admitted": [
                    {
                        "skill_id": e.skill_id,
                        "note": e.note,
                        **(
                            {"source_sha256": e.source_sha256}
                            if e.source_sha256
                            else {}
                        ),
                    }
                    for e in sorted(entries, key=lambda x: x.skill_id)
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return target
