from __future__ import annotations

"""Hardware and mock drivers for peripherals (src/jarvis/adapters/peripherals/drivers.py)."""

import hashlib
import time
from typing import Any, Mapping, Sequence


class MockGPIODriver:
    """In-memory mock driver for GPIO digital pins and PWM."""

    def __init__(self) -> None:
        self.pin_states: dict[int, int] = {}
        self.pin_modes: dict[int, str] = {}
        self.pwm_states: dict[int, dict[str, float]] = {}

    def write_pin(self, pin: int, value: int, mode: str = "out") -> dict[str, Any]:
        val = 1 if value else 0
        self.pin_modes[pin] = mode
        self.pin_states[pin] = val
        return {"pin": pin, "value": val, "mode": mode, "ok": True}

    def read_pin(self, pin: int, mode: str = "in") -> dict[str, Any]:
        self.pin_modes[pin] = mode
        val = self.pin_states.get(pin, 0)
        return {"pin": pin, "value": val, "mode": mode, "ok": True}

    def set_pwm(self, pin: int, duty_cycle: float, frequency_hz: float) -> dict[str, Any]:
        if not (0.0 <= duty_cycle <= 1.0):
            raise ValueError(f"Duty cycle must be in range [0.0, 1.0], got {duty_cycle}")
        if frequency_hz <= 0:
            raise ValueError(f"Frequency must be positive, got {frequency_hz}")
        self.pwm_states[pin] = {"duty_cycle": duty_cycle, "frequency_hz": frequency_hz}
        return {
            "pin": pin,
            "duty_cycle": duty_cycle,
            "frequency_hz": frequency_hz,
            "ok": True,
        }


class MockSensorDriver:
    """In-memory mock sensor telemetry driver."""

    def __init__(self) -> None:
        self.sensor_data: dict[str, dict[str, float]] = {
            "environment_1": {"temperature_c": 22.4, "humidity_pct": 48.2, "pressure_hpa": 1013.25},
            "imu_1": {"accel_x": 0.01, "accel_y": 0.02, "accel_z": 9.81},
            "battery_1": {"voltage_v": 3.78, "charge_pct": 85.0},
        }

    def read_metrics(self, sensor_id: str, metric_types: Sequence[str] | None = None) -> dict[str, Any]:
        data = self.sensor_data.get(sensor_id, {"value": 0.0})
        if metric_types:
            filtered = {k: v for k, v in data.items() if k in metric_types}
        else:
            filtered = dict(data)
        return {
            "sensor_id": sensor_id,
            "metrics": filtered,
            "timestamp": time.time(),
            "ok": True,
        }


class MockSerialDriver:
    """In-memory mock serial communication driver."""

    def __init__(self) -> None:
        self.out_buffers: dict[str, bytearray] = {}
        self.in_buffers: dict[str, bytearray] = {}

    def write_bytes(self, port: str, baud_rate: int, data_bytes: bytes) -> dict[str, Any]:
        buf = self.out_buffers.setdefault(port, bytearray())
        buf.extend(data_bytes)
        sha = hashlib.sha256(data_bytes).hexdigest()
        return {
            "port": port,
            "baud_rate": baud_rate,
            "bytes_written": len(data_bytes),
            "sha256": sha,
            "ok": True,
        }

    def read_bytes(self, port: str, baud_rate: int, max_bytes: int = 256) -> dict[str, Any]:
        buf = self.in_buffers.setdefault(port, bytearray())
        chunk = bytes(buf[:max_bytes])
        del buf[:max_bytes]
        return {
            "port": port,
            "baud_rate": baud_rate,
            "data_hex": chunk.hex(),
            "bytes_read": len(chunk),
            "ok": True,
        }


class MockCameraDriver:
    """In-memory mock camera driver providing deterministic frame captures."""

    def capture_frame(
        self,
        device_id: str = "cam0",
        resolution: tuple[int, int] = (640, 480),
        format: str = "jpeg",
    ) -> dict[str, Any]:
        dummy_bytes = f"FRAME:{device_id}:{resolution[0]}x{resolution[1]}:{format}".encode("utf-8")
        sha = hashlib.sha256(dummy_bytes).hexdigest()
        return {
            "device_id": device_id,
            "resolution": resolution,
            "format": format,
            "bytes_length": len(dummy_bytes),
            "frame_sha256": sha,
            "ok": True,
        }
