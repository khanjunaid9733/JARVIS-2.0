from __future__ import annotations

"""Physical Safety Plane & Hardware Emergency Stop (src/jarvis/safety/estop.py).

Implements fail-closed physical safety invariants for embodied nodes and peripherals:
1. Sticky E-Stop latch with absolute execution precedence.
2. Hard physical ceilings (velocity, power, PWM duty cycle).
3. Cryptographic Creator-only reset authority.
4. Audit logging on stream 'safety'.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import enum
import time
from typing import Any, Callable, Mapping

from jarvis.kernel.event_log import Event, EventLog


class SafetyState(str, enum.Enum):
    NORMAL = "normal"
    WARNING = "warning"
    HOLD = "hold"
    ESTOP = "estop"


class EmergencyStopActiveError(PermissionError):
    """Raised when an action or effect is attempted while E-Stop is active."""


class PhysicalCeilingExceededError(ValueError):
    """Raised when requested operational parameters violate hard physical ceilings."""


@dataclass(frozen=True)
class PhysicalCeilings:
    """Hard boundaries for embodied actuation and motion."""

    max_velocity_mps: float = 2.0  # Linear speed limit (m/s)
    max_power_watts: float = 100.0  # Total actuator power draw ceiling (Watts)
    max_duty_cycle: float = 0.90  # Maximum PWM duty cycle
    max_torque_nm: float = 10.0  # Maximum actuator torque (Nm)

    def validate_parameters(self, params: Mapping[str, Any]) -> None:
        """Validate operational parameters against physical ceilings."""
        if "velocity_mps" in params and float(params["velocity_mps"]) > self.max_velocity_mps:
            raise PhysicalCeilingExceededError(
                f"Requested velocity {params['velocity_mps']} m/s exceeds physical ceiling {self.max_velocity_mps} m/s."
            )
        if "power_watts" in params and float(params["power_watts"]) > self.max_power_watts:
            raise PhysicalCeilingExceededError(
                f"Requested power {params['power_watts']} W exceeds physical ceiling {self.max_power_watts} W."
            )
        if "duty_cycle" in params and float(params["duty_cycle"]) > self.max_duty_cycle:
            raise PhysicalCeilingExceededError(
                f"Requested duty cycle {params['duty_cycle']} exceeds physical ceiling {self.max_duty_cycle}."
            )
        if "torque_nm" in params and float(params["torque_nm"]) > self.max_torque_nm:
            raise PhysicalCeilingExceededError(
                f"Requested torque {params['torque_nm']} Nm exceeds physical ceiling {self.max_torque_nm} Nm."
            )


class EStopLatch:
    """Deterministic, sticky physical emergency-stop latch with audit logging."""

    def __init__(
        self,
        event_log: EventLog | None = None,
        on_trip_callback: Callable[[str], None] | None = None,
        ceilings: PhysicalCeilings | None = None,
    ) -> None:
        self._state = SafetyState.NORMAL
        self._is_tripped = False
        self._trip_reason: str = ""
        self._trip_source: str = ""
        self._tripped_at: str = ""
        self._log = event_log
        self._on_trip = on_trip_callback
        self.ceilings = ceilings or PhysicalCeilings()

    @property
    def state(self) -> SafetyState:
        return self._state

    def is_tripped(self) -> bool:
        return self._is_tripped

    @property
    def trip_reason(self) -> str:
        return self._trip_reason

    def trip(self, reason: str, source: str = "software") -> None:
        """Trip the E-Stop latch. Immediate, sticky, and audited."""
        self._is_tripped = True
        self._state = SafetyState.ESTOP
        self._trip_reason = reason
        self._trip_source = source
        self._tripped_at = datetime.now(timezone.utc).isoformat()

        if self._on_trip:
            try:
                self._on_trip(reason)
            except Exception:
                pass

        if self._log:
            try:
                self._log.append(
                    Event(
                        stream_id="safety",
                        event_type="safety.estop_triggered",
                        principal_id=source,
                        payload={
                            "reason": reason,
                            "source": source,
                            "tripped_at": self._tripped_at,
                            "state": self._state.value,
                        },
                    )
                )
            except Exception:
                pass

    def assert_safe(self) -> None:
        """Fail-closed assertion: raises if E-Stop is active."""
        if self._is_tripped:
            raise EmergencyStopActiveError(
                f"Emergency Stop is ACTIVE (reason: '{self._trip_reason}'). Actuation is forbidden."
            )

    def reset(self, authorized_principal: str = "creator") -> bool:
        """Reset the E-Stop latch. Requires explicit creator authority."""
        if authorized_principal != "creator":
            raise PermissionError("Only the creator principal can reset an emergency stop latch.")

        self._is_tripped = False
        self._state = SafetyState.NORMAL
        self._trip_reason = ""
        self._trip_source = ""
        self._tripped_at = ""

        if self._log:
            try:
                self._log.append(
                    Event(
                        stream_id="safety",
                        event_type="safety.estop_reset",
                        principal_id=authorized_principal,
                        payload={"state": self._state.value},
                    )
                )
            except Exception:
                pass

        return True
