from __future__ import annotations

"""Always-On Living Daemon and Lifecycle Management (src/jarvis/deployment/daemon.py).

Provides continuous system persistence, lifecycle supervision, OS signal handling,
graceful teardown, and periodic health checks per Milestone M6.1.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import enum
import signal
import sys
import threading
import time
from typing import Any, Callable, Mapping

from jarvis.kernel.event_log import Event, EventLog
from jarvis.safety.estop import EStopLatch, SafetyState


class DaemonState(str, enum.Enum):
    UNINITIALIZED = "uninitialized"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass(frozen=True)
class DaemonConfig:
    """Configuration parameters for the living daemon."""

    tick_interval_seconds: float = 1.0
    heartbeat_event_interval_seconds: float = 60.0
    shutdown_timeout_seconds: float = 5.0
    enable_signal_handlers: bool = True
    node_id: str = "workstation_primary"


class LivingDaemon:
    """Always-on living supervisor daemon for JARVIS 2.0."""

    def __init__(
        self,
        event_log: EventLog,
        estop_latch: EStopLatch | None = None,
        config: DaemonConfig | None = None,
        on_tick: Callable[[], None] | None = None,
    ) -> None:
        self.log = event_log
        self.safety = estop_latch or EStopLatch(event_log=event_log)
        self.config = config or DaemonConfig()
        self.on_tick = on_tick

        self._state = DaemonState.UNINITIALIZED
        self._started_at_monotonic: float = 0.0
        self._started_at_iso: str = ""
        self._last_tick_monotonic: float = 0.0
        self._last_heartbeat_monotonic: float = 0.0
        self._tick_count: int = 0
        self._shutdown_requested = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()

    @property
    def state(self) -> DaemonState:
        with self._lock:
            return self._state

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def uptime_seconds(self) -> float:
        if self._started_at_monotonic == 0.0:
            return 0.0
        return time.monotonic() - self._started_at_monotonic

    def start(self, background: bool = True) -> None:
        """Initialize and start the living daemon."""
        with self._lock:
            if self._state in (DaemonState.RUNNING, DaemonState.STARTING):
                return

            self._state = DaemonState.STARTING
            self._shutdown_requested.clear()
            self._started_at_monotonic = time.monotonic()
            self._started_at_iso = datetime.now(timezone.utc).isoformat()
            self._last_tick_monotonic = self._started_at_monotonic
            self._last_heartbeat_monotonic = self._started_at_monotonic

            # Append daemon.started event to stream 'daemon'
            self.log.append(
                Event(
                    stream_id="daemon",
                    event_type="daemon.started",
                    principal_id="system",
                    payload={
                        "node_id": self.config.node_id,
                        "started_at": self._started_at_iso,
                        "config": {
                            "tick_interval_seconds": self.config.tick_interval_seconds,
                        },
                    },
                )
            )

            if self.config.enable_signal_handlers and threading.current_thread() is threading.main_thread():
                self._register_signals()

            self._state = DaemonState.RUNNING

            if background:
                self._thread = threading.Thread(
                    target=self._run_loop, name="LivingDaemonThread", daemon=True
                )
                self._thread.start()

    def _register_signals(self) -> None:
        """Register OS termination signal handlers."""
        def _handle_signal(signum: int, frame: Any) -> None:
            sig_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
            self.stop(reason=f"Received signal {sig_name}")

        try:
            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)
        except (ValueError, AttributeError):
            pass

    def tick(self) -> dict[str, Any]:
        """Execute one deterministic daemon cycle."""
        with self._lock:
            if self._state not in (DaemonState.RUNNING, DaemonState.PAUSED):
                return {"state": self._state.value, "ticked": False}

            now = time.monotonic()
            self._last_tick_monotonic = now
            self._tick_count += 1

            # Execute caller tick callback
            if self.on_tick and self._state == DaemonState.RUNNING:
                try:
                    self.on_tick()
                except Exception:
                    pass

            # Heartbeat logging if interval elapsed
            if now - self._last_heartbeat_monotonic >= self.config.heartbeat_event_interval_seconds:
                self._last_heartbeat_monotonic = now
                try:
                    self.log.append(
                        Event(
                            stream_id="daemon",
                            event_type="daemon.heartbeat",
                            principal_id="system",
                            payload={
                                "uptime_seconds": self.uptime_seconds,
                                "tick_count": self._tick_count,
                                "safety_state": self.safety.state.value,
                            },
                        )
                    )
                except Exception:
                    pass

            return {
                "state": self._state.value,
                "ticked": True,
                "tick_count": self._tick_count,
                "uptime_seconds": self.uptime_seconds,
                "safety_state": self.safety.state.value,
            }

    def _run_loop(self) -> None:
        """Internal daemon loop when running in background thread."""
        while not self._shutdown_requested.is_set():
            self.tick()
            self._shutdown_requested.wait(timeout=self.config.tick_interval_seconds)

    def pause(self) -> None:
        with self._lock:
            if self._state == DaemonState.RUNNING:
                self._state = DaemonState.PAUSED

    def resume(self) -> None:
        with self._lock:
            if self._state == DaemonState.PAUSED:
                self._state = DaemonState.RUNNING

    def stop(self, reason: str = "normal_shutdown") -> None:
        """Gracefully stop the daemon and flush resources."""
        with self._lock:
            if self._state in (DaemonState.STOPPED, DaemonState.STOPPING):
                return

            self._state = DaemonState.STOPPING
            self._shutdown_requested.set()

            # Append daemon.stopped event to log
            try:
                self.log.append(
                    Event(
                        stream_id="daemon",
                        event_type="daemon.stopped",
                        principal_id="system",
                        payload={
                            "reason": reason,
                            "uptime_seconds": self.uptime_seconds,
                            "tick_count": self._tick_count,
                            "stopped_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                )
            except Exception:
                pass

            self._state = DaemonState.STOPPED

        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=self.config.shutdown_timeout_seconds)

    def health_status(self) -> dict[str, Any]:
        """Return diagnostic health snapshot of the daemon."""
        with self._lock:
            cur = self.log._conn.execute("SELECT COUNT(*) AS total_events, MAX(seq) AS last_seq FROM events")
            row = cur.fetchone()
            return {
                "node_id": self.config.node_id,
                "state": self._state.value,
                "uptime_seconds": self.uptime_seconds,
                "tick_count": self._tick_count,
                "safety_state": self.safety.state.value,
                "estop_tripped": self.safety.is_tripped(),
                "total_events": int(row["total_events"] or 0),
                "last_seq": int(row["last_seq"] or 0),
                "started_at": self._started_at_iso,
                "healthy": self._state in (DaemonState.RUNNING, DaemonState.PAUSED) and not self.safety.is_tripped(),
            }
