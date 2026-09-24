# M5.4 — Peripheral Control & IoT Capability Contracts (Kickoff & Design Contract)

**Status:** ACCEPTED DESIGN — architectural contract for implementation.  
**Author/owner:** Antigravity (Gemini) designs & verifies; Big Pickle (OpenCode) implements.  
**Milestone:** Phase 4: M5 (Embodiment & External Device Nodes), package M5.4.  
**Baseline:** `task/supervisor @ 04c5100`, **843 passed**, 0 failed.  
**Proof Target (M5.4):** `contract invoke -> pin/port jail validation -> prepare envelope -> commit hardware effect -> verify postcondition -> telemetry read`.

---

## 1. Why This Exists

JARVIS's physical embodiment (Milestones M5–M7) requires controlling physical hardware actuators and reading environmental sensors across companion bodies, microcontrollers, and IoT hubs.

To prevent physical damage, runaway actuators, or security compromises:
1. **External Capability Substitution Seam**: No raw hardware libraries (`RPi.GPIO`, `pyserial`, `opencv`) may be imported into the core kernel. Hardware drivers sit strictly behind `ProviderAdapter` interfaces.
2. **Pin & Port Jailing**: Just as `FilesystemSandbox` jails file operations to the workspace, peripheral control must enforce strict **Pin Jails** (preventing writes to system/reset pins) and **Port Jails** (preventing arbitrary serial execution on untrusted COM/tty ports).
3. **EffectEnvelope Governance**: Hardware mutations (GPIO digital/PWM writes, serial transmissions) must execute through the two-phase `EffectEnvelopeEngine` (prepare -> authorize -> commit -> verify).
4. **Mockability & Determinism**: All peripheral operations must be fully testable without physical hardware attached.

---

## 2. Grounding in Existing Modules

- **`src/jarvis/kernel/registry.py`**: `ProviderAdapter` protocol (`invoke`, `health_check`, `provider_id`).
- **`src/jarvis/kernel/effect_envelope.py`**: `EffectEnvelopeEngine`, `EffectRequest`, `EffectResult`, postcondition verification.
- **`src/jarvis/effects/filesystem.py`**: Jailing patterns (`PathJailError`).

---

## 3. Detailed Design Contract

### A. Jailing & Errors (`src/jarvis/adapters/peripherals/jails.py`)

- `PinJailError(PermissionError)`: Raised if a GPIO pin is outside `allowed_pins` or in `reserved_pins`.
- `PortJailError(PermissionError)`: Raised if a serial port is outside `allowed_ports`.
- `PeripheralExecutionError(RuntimeError)`: Raised on hardware or driver communication failure.

### B. Contracts (`src/jarvis/adapters/peripherals/contracts.py`)

- `peripheral.gpio.write`: `pin: int, value: int, mode: str = "out"`
- `peripheral.gpio.read`: `pin: int, mode: str = "in"`
- `peripheral.gpio.pwm`: `pin: int, duty_cycle: float, frequency_hz: float`
- `peripheral.sensor.read`: `sensor_id: str, metric_types: Sequence[str]`
- `peripheral.serial.write`: `port: str, baud_rate: int, data_hex: str`
- `peripheral.serial.read`: `port: str, baud_rate: int, timeout_ms: int`
- `camera.capture`: `device_id: str, resolution: tuple[int, int], format: str`

### C. Adapter (`src/jarvis/adapters/peripherals/adapter.py`)

`PeripheralAdapter(ProviderAdapter)`:
- Backed by configurable drivers (`MockGPIODriver`, `MockSensorDriver`, `MockSerialDriver`, `MockCameraDriver`).
- Dispatches `invoke(contract_id, version, args)` enforcing pin and port jailing.
- Fully compatible with `EffectEnvelopeEngine`.

---

## 4. Test Suite Requirements (`tests/adapters/test_peripherals.py`)

1. **`test_gpio_write_and_read_success`**: Valid pin write updates state, subsequent read returns matching value.
2. **`test_gpio_pin_jail_rejects_disallowed_pins`**: Writing to an unlisted pin raises `PinJailError`.
3. **`test_gpio_pin_jail_rejects_reserved_pins`**: Writing to a reserved system pin (e.g., reset, ground) raises `PinJailError`.
4. **`test_gpio_pwm_validation`**: Duty cycle outside [0.0, 1.0] or negative frequency raises `ValueError`.
5. **`test_serial_port_jail_rejects_unauthorized_ports`**: Writing to unauthorized port raises `PortJailError`.
6. **`test_serial_write_and_read_roundtrip`**: Writing hex data to jailed mock port delivers bytes to mock buffer.
7. **`test_sensor_telemetry_read`**: Reading sensor metrics returns expected dictionary of floats.
8. **`test_camera_frame_capture`**: Camera capture returns valid frame metadata and sha256.
9. **`test_effect_envelope_peripheral_execution`**: Invoking GPIO write through `EffectEnvelopeEngine` verifies declared postconditions and records effect event.
