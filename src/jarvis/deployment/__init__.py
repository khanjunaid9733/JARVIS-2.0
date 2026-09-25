"""Living Deployment & Always-On Persistence package for JARVIS (Milestone M6)."""

from __future__ import annotations

from .backup import (
    BackupManifest,
    CheckpointStats,
    LedgerBackupManager,
)
from .daemon import DaemonConfig, DaemonState, LivingDaemon
from .scheduler import (
    AutonomousScheduler,
    ScheduledMission,
)
from .tunnel import (
    AuthenticationFailedError,
    HandshakeHello,
    HandshakeWelcome,
    ReplayAttackError,
    SecureTunnelEndpoint,
    TunnelSecurityError,
    TunnelState,
)
from .wakeword import (
    MockWakeWordDetector,
    WakeWordCoordinator,
    WakeWordDetector,
    WakeWordResult,
)

__all__ = [
    "AuthenticationFailedError",
    "AutonomousScheduler",
    "BackupManifest",
    "CheckpointStats",
    "DaemonConfig",
    "DaemonState",
    "HandshakeHello",
    "HandshakeWelcome",
    "LedgerBackupManager",
    "LivingDaemon",
    "MockWakeWordDetector",
    "ReplayAttackError",
    "ScheduledMission",
    "SecureTunnelEndpoint",
    "TunnelSecurityError",
    "TunnelState",
    "WakeWordCoordinator",
    "WakeWordDetector",
    "WakeWordResult",
]
