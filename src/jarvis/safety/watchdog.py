from __future__ import annotations

"""Hardware and process watchdog timer for physical safety (src/jarvis/safety/watchdog.py).

Monitors node health and periodic heartbeats. Trips the safety plane fail-closed
if heartbeats stall or process hangs.
"""

import time
from typing import Callable

from jarvis.safety.estop import EStopLatch


class HeartbeatWatchdog:
    """Fail-closed heartbeat watchdog for embodied nodes and peripherals."""

    def __init__(
        self,
        estop_latch: EStopLatch,
        timeout_seconds: float = 2.0,
        on_timeout: Callable[[], None] | None = None,
    ) -> None:
        self.latch = estop_latch
        self.timeout_seconds = timeout_seconds
        self.on_timeout = on_timeout
        self._last_pet: float = time.monotonic()
        self._is_running = True

    @property
    def last_pet(self) -> float:
        return self._last_pet

    def pet(self, source: str = "heartbeat") -> None:
        """Reset the watchdog countdown with an incoming heartbeat."""
        self._last_pet = time.monotonic()

    def check_timeout(self, now: float | None = None) -> bool:
        """Check if time since last pet exceeds timeout threshold.
        
        Returns True if timed out (and trips the safety latch), False otherwise.
        """
        if not self._is_running:
            return False

        current_time = now if now is not None else time.monotonic()
        elapsed = current_time - self._last_pet

        if elapsed > self.timeout_seconds:
            self.latch.trip(
                reason=f"Watchdog timeout: {elapsed:.2f}s elapsed without heartbeat (threshold {self.timeout_seconds:.2f}s)",
                source="watchdog",
            )
            if self.on_timeout:
                try:
                    self.on_timeout()
                except Exception:
                    pass
            return True

        return False

    def stop(self) -> None:
        self._is_running = False

    def start(self) -> None:
        self._is_running = True
        self._last_pet = time.monotonic()
