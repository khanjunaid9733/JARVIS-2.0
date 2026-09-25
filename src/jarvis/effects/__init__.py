from __future__ import annotations

"""Hermetic Effects Package (Milestones M2.6, M7.2, spec §83 / §24).

Provides concrete, sandboxed provider adapters for external world effects
operating behind `jarvis.kernel.effect_envelope.EffectEnvelopeEngine`.
"""

from .computer_use import (
    ComputerUseDriverProtocol,
    ComputerUseExecutor,
    ComputerUseSecurityError,
    DeliveryMode,
    GUIAction,
    GUIActionType,
    MockComputerUseDriver,
)
from .filesystem import (
    BackupRecord,
    FilesystemEffectAdapter,
    FilesystemSandbox,
    PathJailError,
)

__all__ = [
    "BackupRecord",
    "ComputerUseDriverProtocol",
    "ComputerUseExecutor",
    "ComputerUseSecurityError",
    "DeliveryMode",
    "FilesystemEffectAdapter",
    "FilesystemSandbox",
    "GUIAction",
    "GUIActionType",
    "MockComputerUseDriver",
    "PathJailError",
]
