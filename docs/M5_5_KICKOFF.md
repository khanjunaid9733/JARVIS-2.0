# M5.5 — Physical Safety Plane & Hardware E-Stop (Kickoff & Design Contract)

**Status:** ACCEPTED DESIGN — architectural contract for implementation.  
**Author/owner:** Antigravity (Gemini) designs & verifies; Big Pickle (OpenCode) implements.  
**Milestone:** Phase 4: M5 (Embodiment & External Device Nodes), package M5.5 (Final M5 Package).  
**Baseline:** `task/supervisor @ 6f79bb4`, **852 passed**, 0 failed.  
**Proof Target (M5.5):** `physical ceilings -> watchdog heartbeat -> e-stop latch -> <50ms actuator cut -> sticky creator reset -> audit event log`.

---

## 1. Why This Exists

Physical embodiment introduces irreversible real-world risk: robotic arms can collide, motor controllers can run away, and power electronics can overheat.

Milestone M5.5 establishes the non-negotiable **Physical Safety Plane**:
1. **E-Stop Precedence (Hard Latch)**: When an emergency stop is signaled (software command, hardware switch, or sensor threshold), it has absolute precedence over all planners, missions, and threads. Actuator power/signals must be severed immediately (latency target ≤50ms).
2. **Sticky Latch Discipline**: Once an E-Stop is tripped, it is latched. Software cannot self-recover or clear its own E-Stop. Clearing requires explicit cryptographic Creator authorization (`principal_id == "creator"`).
3. **Physical Ceilings Invariants**: Maximum velocity (m/s), maximum angular rate, power envelopes, and PWM duty cycles are bounded by hard invariants. Any effect request exceeding these ceilings is rejected before execution.
4. **Heartbeat Watchdog (Fail-Closed Disconnection)**: Any embodied node or actuator connection requires active, continuous heartbeat pets. A dead connection or hanging process trips the watchdog within a timeout threshold, automatically cutting actuator holds.
5. **Auditable Event Sourcing**: Every state transition (`NORMAL -> WARNING -> HOLD -> ESTOP`) is recorded to the canonical `EventLog` on stream `safety`.

---

## 2. Grounding in Existing Modules

- **`src/jarvis/kernel/event_log.py`**: `EventLog` for recording `safety.estop_triggered` and `safety.state_changed` audit events.
- **`src/jarvis/kernel/effect_envelope.py`**: `EffectEnvelopeEngine` integration ensuring effects fail-closed when E-Stop is active.
- **`src/jarvis/adapters/peripherals/`**: Physical actuators (GPIO, PWM, Serial) halted on E-Stop.

---

## 3. Detailed Design Contract

### A. Data Structures & State Machine (`src/jarvis/safety/estop.py`)

```python
class SafetyState(str, enum.Enum):
    NORMAL = "normal"
    WARNING = "warning"
    HOLD = "hold"
    ESTOP = "estop"

class EmergencyStopActiveError(PermissionError):
    """Raised when an operation is attempted while E-Stop is latched."""

class PhysicalCeilingExceededError(ValueError):
    """Raised when an effect exceeds configured physical safety ceilings."""
```

### B. EStopLatch & SafetyMonitor

- `EStopLatch`:
  - `trip(reason: str, source: str = "software") -> None`
  - `is_tripped() -> bool`
  - `assert_safe() -> None`
  - `reset(authorized_principal: str = "creator") -> bool`
- `PhysicalCeilings`:
  - `max_velocity_mps: float`
  - `max_power_watts: float`
  - `max_duty_cycle: float`
  - `validate_parameters(params: Mapping[str, Any]) -> None`

### C. Watchdog (`src/jarvis/safety/watchdog.py`)

- `HeartbeatWatchdog`:
  - `timeout_seconds: float`
  - `pet(source: str = "heartbeat") -> None`
  - `check_timeout() -> bool` (trips safety plane if time since last pet > timeout)
  - `start() / stop()`

---

## 4. Test Suite Requirements (`tests/safety/test_estop.py`)

1. **`test_estop_latch_trips_immediately`**: Tripping E-Stop transitions state to `ESTOP` and sets `is_tripped() == True`.
2. **`test_estop_precedence_blocks_effect_dispatch`**: When tripped, `assert_safe()` raises `EmergencyStopActiveError`.
3. **`test_estop_latch_is_sticky_until_creator_reset`**: Unauthenticated reset raises error; creator reset clears latch and returns to `NORMAL`.
4. **`test_physical_ceilings_reject_excessive_velocity_or_power`**: Parameter exceeding velocity or power ceiling raises `PhysicalCeilingExceededError`.
5. **`test_watchdog_timeout_triggers_fail_closed_estop`**: Time elapsed without pet triggers E-Stop latch and sets state to `ESTOP`.
6. **`test_watchdog_petting_prevents_timeout`**: Regular petting maintains `NORMAL` state.
7. **`test_e_stop_reaction_latency_under_50ms`**: Tripping latch and checking safety response executes in <50ms.
8. **`test_safety_event_logging`**: E-Stop trips append `safety.estop_triggered` event with reason and source to `EventLog`.
