from __future__ import annotations

"""Hermetic Effects Package (Milestone M2.6, spec §83).

Provides concrete, sandboxed provider adapters for external world effects
operating behind `jarvis.kernel.effect_envelope.EffectEnvelopeEngine`.
"""

from .filesystem import (
    BackupRecord,
    FilesystemEffectAdapter,
    FilesystemSandbox,
    PathJailError,
)

__all__ = [
    "BackupRecord",
    "FilesystemEffectAdapter",
    "FilesystemSandbox",
    "PathJailError",
]
