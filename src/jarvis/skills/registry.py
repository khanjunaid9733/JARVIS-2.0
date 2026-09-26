from __future__ import annotations

"""In-memory Skill Registry with inverted index and semantic token matching.

Provides fast, deterministic lookup and relevance ranking across hundreds of
loaded skills without external vector database dependencies.
"""

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from .manifest import SkillManifest, load_skills_directory


@dataclass(frozen=True)
class SkillMatch:
    """Result of a skill query match."""

    skill: SkillManifest
    score: float
    matched_terms: tuple[str, ...] = ()


def _tokenize(text: str) -> list[str]:
    """Normalize text into lowercase alphanumeric tokens."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    # Filter very short common tokens
    stopwords = {
        "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with",
        "of", "by", "is", "it", "this", "that", "from", "as", "any", "all",
    }
    return [t for t in tokens if len(t) > 1 and t not in stopwords]


class SkillRegistry:
    """In-memory registry and search index for JARVIS skills."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillManifest] = {}
        self._domain_index: dict[str, set[str]] = defaultdict(set)
        # Inverted index: term -> dict[skill_id, weight]
        self._inverted_index: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._doc_lengths: dict[str, int] = {}
        self._total_doc_len: int = 0
        self._avg_doc_len: float = 1.0

    def _remove_from_index(self, skill_id: str) -> None:
        """Remove a skill from the inverted index and domain mapping before re-indexing."""
        old_skill = self._skills.get(skill_id)
        if old_skill is not None:
            self._domain_index[old_skill.domain].discard(skill_id)
            if not self._domain_index[old_skill.domain]:
                self._domain_index.pop(old_skill.domain, None)

        for term, postings in list(self._inverted_index.items()):
            if skill_id in postings:
                del postings[skill_id]
                if not postings:
                    del self._inverted_index[term]

        old_len = self._doc_lengths.pop(skill_id, 0)
        self._total_doc_len -= old_len
        if self._doc_lengths:
            self._avg_doc_len = self._total_doc_len / len(self._doc_lengths)
        else:
            self._avg_doc_len = 1.0

    def unregister(self, skill_id: str) -> bool:
        """Unregister a skill by ID and purge all index postings."""
        if skill_id not in self._skills:
            return False
        self._remove_from_index(skill_id)
        del self._skills[skill_id]
        return True

    def register(self, skill: SkillManifest) -> None:
        """Register a single skill into the registry and update indexes."""
        if skill.id in self._skills:
            self._remove_from_index(skill.id)

        self._skills[skill.id] = skill
        self._domain_index[skill.domain].add(skill.id)

        # Index tokens with field weighting
        field_tokens: list[tuple[list[str], float]] = [
            # Field, weight boost
            (_tokenize(skill.id.replace("-", " ")), 10.0),
            (_tokenize(skill.title), 4.0),
            (_tokenize(skill.domain), 3.0),
            (_tokenize(skill.description), 2.0),
        ]
        for trigger in skill.triggers:
            field_tokens.append((_tokenize(trigger), 6.0))

        total_tokens = 0
        for tokens, weight in field_tokens:
            for token in tokens:
                self._inverted_index[token][skill.id] += weight
                total_tokens += 1

        new_len = max(1, total_tokens)
        self._doc_lengths[skill.id] = new_len
        self._total_doc_len += new_len
        self._avg_doc_len = self._total_doc_len / len(self._doc_lengths)

    def get(self, skill_id: str) -> SkillManifest | None:
        """Retrieve a skill by its exact ID."""
        return self._skills.get(skill_id)

    def contains(self, skill_id: str) -> bool:
        """Check if a skill ID is registered."""
        return skill_id in self._skills

    def count(self) -> int:
        """Total number of registered skills."""
        return len(self._skills)

    def list_all(self) -> list[SkillManifest]:
        """List all registered skills ordered by ID."""
        return [self._skills[k] for k in sorted(self._skills.keys())]

    def list_domains(self) -> list[str]:
        """List all unique domain categories."""
        return sorted(self._domain_index.keys())

    def get_by_domain(self, domain: str) -> list[SkillManifest]:
        """Get all skills belonging to a specific domain."""
        ids = self._domain_index.get(domain, set())
        return [self._skills[i] for i in sorted(ids)]

    def find(
        self,
        query: str,
        domain: str | None = None,
        min_score: float = 0.5,
        limit: int = 10,
    ) -> list[SkillMatch]:
        """Search skills by natural language query or keywords.

        Uses BM25-style term frequency and inverse document frequency scoring
        with domain constraints.
        """
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores: dict[str, float] = defaultdict(float)
        matched_terms: dict[str, set[str]] = defaultdict(set)
        num_docs = max(1, len(self._skills))

        # Filter candidate pool if domain specified
        candidate_ids = self._domain_index.get(domain) if domain else set(self._skills.keys())
        if not candidate_ids:
            return []

        for token in query_tokens:
            postings = self._inverted_index.get(token)
            if not postings:
                continue

            # Inverse Document Frequency (IDF)
            df = len(postings)
            idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)
            idf = max(0.2, idf)

            for skill_id, weight in postings.items():
                if skill_id not in candidate_ids:
                    continue
                # Term Frequency with length normalization
                doc_len = self._doc_lengths.get(skill_id, self._avg_doc_len)
                tf_norm = weight / (weight + 1.5 * (0.25 + 0.75 * (doc_len / self._avg_doc_len)))
                score = idf * tf_norm * 5.0
                scores[skill_id] += score
                matched_terms[skill_id].add(token)

        # Exact ID match boost
        normalized_q = query.strip().lower().replace(" ", "-")
        if normalized_q in self._skills:
            scores[normalized_q] += 50.0
            matched_terms[normalized_q].add(normalized_q)

        # Build and sort matches
        results: list[SkillMatch] = []
        for skill_id, score in scores.items():
            if score >= min_score and skill_id in self._skills:
                results.append(
                    SkillMatch(
                        skill=self._skills[skill_id],
                        score=round(score, 3),
                        matched_terms=tuple(sorted(matched_terms[skill_id])),
                    )
                )

        results.sort(key=lambda m: m.score, reverse=True)
        return results[:limit]

    def load_from_directory(self, directory: Path | str) -> int:
        """Load all skills found in a directory. Returns count of loaded skills."""
        loaded = load_skills_directory(directory)
        for skill in loaded.values():
            self.register(skill)
        return len(loaded)


_GLOBAL_REGISTRY: SkillRegistry | None = None


def get_default_registry() -> SkillRegistry:
    """Retrieve or build the singleton SkillRegistry loaded from default locations."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is not None:
        return _GLOBAL_REGISTRY

    registry = SkillRegistry()

    # Search in .agents/skills relative to common roots
    search_paths = [
        Path(".agents/skills"),
        Path("f:/JARVIS2.0/.agents/skills"),
        Path.cwd() / ".agents" / "skills",
    ]

    for p in search_paths:
        if p.is_dir():
            registry.load_from_directory(p)
            break

    _GLOBAL_REGISTRY = registry
    return _GLOBAL_REGISTRY
