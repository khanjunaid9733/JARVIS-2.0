from __future__ import annotations

"""Background Autonomous Mission Scheduler (src/jarvis/deployment/scheduler.py).

Provides periodic, cron-like mission dispatching governed by:
1. Physical safety plane gating (M5.5 E-Stop & ceilings).
2. Interval and run-count bounds.
3. Event log audit trail on stream 'scheduler'.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Any, Callable, Mapping, Sequence

from jarvis.kernel.event_log import Event, EventLog
from jarvis.safety.estop import EStopLatch, EmergencyStopActiveError, SafetyState


@dataclass
class ScheduledMission:
    """Specification of a recurring or scheduled background mission."""

    mission_id: str
    name: str
    goal: str
    interval_seconds: float
    enabled: bool = True
    max_runs: int | None = None
    require_safety_normal: bool = True
    last_run_monotonic: float = 0.0
    run_count: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def is_due(self, now: float) -> bool:
        """Evaluate if the task is due for execution."""
        if not self.enabled:
            return False
        if self.max_runs is not None and self.run_count >= self.max_runs:
            return False
        return (now - self.last_run_monotonic) >= self.interval_seconds


class AutonomousScheduler:
    """Supervises recurring and autonomous background missions."""

    def __init__(
        self,
        event_log: EventLog | None = None,
        estop_latch: EStopLatch | None = None,
        dispatcher: Callable[[ScheduledMission], bool] | None = None,
    ) -> None:
        self.log = event_log
        self.safety = estop_latch or EStopLatch(event_log=event_log)
        self.dispatcher = dispatcher
        self._missions: dict[str, ScheduledMission] = {}

    def schedule(self, mission: ScheduledMission) -> None:
        """Register a new scheduled background mission."""
        self._missions[mission.mission_id] = mission
        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="scheduler",
                        event_type="scheduler.mission_registered",
                        principal_id="system",
                        payload={
                            "mission_id": mission.mission_id,
                            "name": mission.name,
                            "interval_seconds": mission.interval_seconds,
                            "max_runs": mission.max_runs,
                        },
                    )
                )
            except Exception:
                pass

    def unschedule(self, mission_id: str) -> bool:
        """Remove a mission from scheduling."""
        if mission_id in self._missions:
            del self._missions[mission_id]
            return True
        return False

    def get_mission(self, mission_id: str) -> ScheduledMission | None:
        return self._missions.get(mission_id)

    def list_missions(self) -> list[ScheduledMission]:
        return list(self._missions.values())

    def tick(self, now: float | None = None) -> list[str]:
        """Check all scheduled missions and dispatch due ones.
        
        Returns a list of mission_ids that executed successfully.
        """
        current_time = now if now is not None else time.monotonic()
        executed_ids: list[str] = []

        for mission in list(self._missions.values()):
            if not mission.is_due(current_time):
                continue

            # 1. Safety Check: If require_safety_normal and E-Stop is active, block execution!
            if mission.require_safety_normal and self.safety.is_tripped():
                if self.log:
                    try:
                        self.log.append(
                            Event(
                                stream_id="scheduler",
                                event_type="scheduler.mission_blocked_by_safety",
                                principal_id="safety_plane",
                                payload={
                                    "mission_id": mission.mission_id,
                                    "safety_state": self.safety.state.value,
                                    "reason": self.safety.trip_reason,
                                },
                            )
                        )
                    except Exception:
                        pass
                continue

            # 2. Dispatch mission
            success = True
            if self.dispatcher:
                try:
                    success = self.dispatcher(mission)
                except Exception:
                    success = False

            mission.last_run_monotonic = current_time
            mission.run_count += 1

            if success:
                executed_ids.append(mission.mission_id)

            # Auto-disable if max runs reached
            if mission.max_runs is not None and mission.run_count >= mission.max_runs:
                mission.enabled = False

            if self.log:
                try:
                    self.log.append(
                        Event(
                            stream_id="scheduler",
                            event_type="scheduler.mission_dispatched",
                            principal_id="system",
                            payload={
                                "mission_id": mission.mission_id,
                                "run_count": mission.run_count,
                                "success": success,
                            },
                        )
                    )
                except Exception:
                    pass

        return executed_ids
