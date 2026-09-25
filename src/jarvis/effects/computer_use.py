"""Background Headless Computer-Use Seam & GUI Action Engine (Milestone M7.2).

Provides:
- GUIActionType: Supported desktop action primitives (click, type, scroll, key).
- DeliveryMode: Background headless messaging (no cursor stealing) vs foreground.
- GUIAction: Formalized, validated desktop action descriptor.
- ComputerUseDriverProtocol: Seam protocol for platform drivers.
- MockComputerUseDriver: Deterministic test driver for headless verification.
- ComputerUseExecutor: Safety-governed action executor integrated with E-Stop and EventLog.
"""

from __future__ import annotations

import enum
from typing import Any, Mapping, Optional, Protocol, Sequence

from pydantic import BaseModel, ConfigDict, Field

from ..kernel.event_log import Event, EventLog, new_ulid
from ..safety.estop import EStopLatch, EmergencyStopActiveError


class GUIActionType(str, enum.Enum):
    """Types of GUI interactions supported by the Computer-Use engine."""

    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    SCROLL = "scroll"
    DRAG = "drag"


class DeliveryMode(str, enum.Enum):
    """Delivery mechanism for GUI actions."""

    BACKGROUND_HEADLESS = "background_headless"  # Dispatches via window messages/UIA without moving physical mouse
    FOREGROUND_EMULATED = "foreground_emulated"  # Moves mouse / sends hardware input with safety gates


class ComputerUseSecurityError(RuntimeError):
    """Base error for GUI automation security failures."""


class GUIAction(BaseModel):
    """Validated descriptor of a computer-use interaction."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    action_id: str = Field(default_factory=lambda: f"act_{new_ulid()}")
    action_type: GUIActionType
    delivery_mode: DeliveryMode = DeliveryMode.BACKGROUND_HEADLESS
    target_window_title: Optional[str] = None
    target_hwnd: Optional[int] = None
    target_element_id: Optional[str] = None
    coordinates: Optional[tuple[int, int]] = None  # (x, y) relative to target or desktop
    text_payload: Optional[str] = None
    key_name: Optional[str] = None
    scroll_delta: Optional[int] = None
    metadata: Mapping[str, Any] = Field(default_factory=dict)


class ComputerUseDriverProtocol(Protocol):
    """Protocol for abstracting OS-level GUI input dispatch."""

    def execute_action(self, action: GUIAction) -> bool: ...

    def get_active_window(self) -> tuple[str, int]: ...

    def list_windows(self) -> list[tuple[str, int]]: ...


class MockComputerUseDriver:
    """Hermetic, testable computer-use driver for unit & integration testing."""

    def __init__(self) -> None:
        self.executed_actions: list[GUIAction] = []
        self.active_window = ("Visual Studio Code", 1001)
        self.available_windows = [
            ("Visual Studio Code", 1001),
            ("Terminal", 1002),
            ("Web Browser", 1003),
        ]
        self._should_fail = False

    def set_should_fail(self, fail: bool) -> None:
        self._should_fail = fail

    def execute_action(self, action: GUIAction) -> bool:
        if self._should_fail:
            return False
        self.executed_actions.append(action)
        return True

    def get_active_window(self) -> tuple[str, int]:
        return self.active_window

    def list_windows(self) -> list[tuple[str, int]]:
        return list(self.available_windows)


class ComputerUseExecutor:
    """Coordinates computer-use execution with physical safety and audit logging."""

    def __init__(
        self,
        driver: Optional[ComputerUseDriverProtocol] = None,
        event_log: Optional[EventLog] = None,
        estop_latch: Optional[EStopLatch] = None,
        allow_foreground: bool = True,
    ) -> None:
        self.driver = driver or MockComputerUseDriver()
        self.log = event_log
        self.safety = estop_latch or EStopLatch(event_log=event_log)
        self.allow_foreground = allow_foreground

    def execute(self, action: GUIAction) -> bool:
        """Executes a computer-use action under safety gating and audit logging.
        
        1. Checks E-Stop status. If tripped, immediately aborts.
        2. If foreground delivery is requested but disallowed, raises error.
        3. Dispatches action to driver.
        4. Logs execution audit event to EventLog.
        """
        # Step 1: Physical safety check
        if self.safety.is_tripped():
            if self.log:
                try:
                    self.log.append(
                        Event(
                            stream_id="effects.computer_use",
                            event_type="computer_use.action_blocked_by_safety",
                            principal_id="safety.estop",
                            payload={
                                "action_id": action.action_id,
                                "action_type": action.action_type.value,
                                "reason": self.safety.trip_reason,
                            },
                        )
                    )
                except Exception:
                    pass
            raise EmergencyStopActiveError(
                f"Cannot execute GUI action {action.action_id}: Emergency Stop is active ({self.safety.trip_reason})"
            )

        # Step 2: Foreground delivery restriction check
        if action.delivery_mode == DeliveryMode.FOREGROUND_EMULATED and not self.allow_foreground:
            raise ComputerUseSecurityError(
                f"Foreground emulation is disabled for action {action.action_id}. "
                "Use DeliveryMode.BACKGROUND_HEADLESS to prevent cursor hijacking."
            )

        # Step 3: Dispatch action
        success = self.driver.execute_action(action)

        # Step 4: Audit logging
        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="effects.computer_use",
                        event_type="computer_use.action_executed" if success else "computer_use.action_failed",
                        principal_id="effects.computer_use_executor",
                        payload={
                            "action_id": action.action_id,
                            "action_type": action.action_type.value,
                            "delivery_mode": action.delivery_mode.value,
                            "target_window": action.target_window_title,
                            "coordinates": action.coordinates,
                            "success": success,
                        },
                    )
                )
            except Exception:
                pass

        return success
