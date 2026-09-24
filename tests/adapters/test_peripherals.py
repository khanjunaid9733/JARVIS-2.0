from __future__ import annotations

import pytest

from jarvis.adapters.peripherals.adapter import PeripheralAdapter
from jarvis.adapters.peripherals.drivers import (
    MockCameraDriver,
    MockGPIODriver,
    MockSensorDriver,
    MockSerialDriver,
)
from jarvis.adapters.peripherals.jails import GPIOPinJail, PinJailError, PortJailError, SerialPortJail
from jarvis.kernel.effect_envelope import EffectEnvelope, EffectEnvelopeEngine
from jarvis.kernel.intent import Budget, Manifest, ResolvedContract
from jarvis.kernel.registry import (
    CapabilityRegistry,
    ContractDef,
    ProviderBinding,
    ProviderMeta,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def adapter():
    return PeripheralAdapter()


async def test_gpio_write_and_read_success(adapter: PeripheralAdapter):
    # Valid GPIO pin 17
    write_res = await adapter.invoke(
        "peripheral.gpio.write", "1.0.0", {"pin": 17, "value": 1, "mode": "out"}
    )
    assert write_res["ok"] is True
    assert write_res["pin"] == 17
    assert write_res["value"] == 1

    read_res = await adapter.invoke("peripheral.gpio.read", "1.0.0", {"pin": 17})
    assert read_res["ok"] is True
    assert read_res["value"] == 1


async def test_gpio_pin_jail_rejects_disallowed_pins(adapter: PeripheralAdapter):
    # Pin 30 is outside allowed range (2..27)
    with pytest.raises(PinJailError) as exc_info:
        await adapter.invoke(
            "peripheral.gpio.write", "1.0.0", {"pin": 30, "value": 1}
        )
    assert "outside the allowed pin jail" in str(exc_info.value)


async def test_gpio_pin_jail_rejects_reserved_pins(adapter: PeripheralAdapter):
    # Pin 14 is a reserved UART/console pin
    with pytest.raises(PinJailError) as exc_info:
        await adapter.invoke(
            "peripheral.gpio.write", "1.0.0", {"pin": 14, "value": 1}
        )
    assert "reserved system pin" in str(exc_info.value)


async def test_gpio_pwm_validation(adapter: PeripheralAdapter):
    # Valid PWM
    pwm_res = await adapter.invoke(
        "peripheral.gpio.pwm",
        "1.0.0",
        {"pin": 18, "duty_cycle": 0.75, "frequency_hz": 2000.0},
    )
    assert pwm_res["ok"] is True
    assert pwm_res["duty_cycle"] == 0.75

    # Invalid duty cycle > 1.0
    with pytest.raises(ValueError) as exc:
        await adapter.invoke(
            "peripheral.gpio.pwm", "1.0.0", {"pin": 18, "duty_cycle": 1.5}
        )
    assert "Duty cycle must be in range" in str(exc.value)

    # Invalid negative frequency
    with pytest.raises(ValueError) as exc:
        await adapter.invoke(
            "peripheral.gpio.pwm",
            "1.0.0",
            {"pin": 18, "duty_cycle": 0.5, "frequency_hz": -10.0},
        )
    assert "Frequency must be positive" in str(exc.value)


async def test_serial_port_jail_rejects_unauthorized_ports(adapter: PeripheralAdapter):
    # COM99 is not in allowed serial port jail
    with pytest.raises(PortJailError) as exc:
        await adapter.invoke(
            "peripheral.serial.write",
            "1.0.0",
            {"port": "COM99", "data_hex": "48656c6c6f"},
        )
    assert "not in the authorized serial port jail" in str(exc.value)


async def test_serial_write_and_read_roundtrip(adapter: PeripheralAdapter):
    # Write to authorized port COM3
    data = "414243"  # "ABC"
    write_res = await adapter.invoke(
        "peripheral.serial.write", "1.0.0", {"port": "COM3", "data_hex": data}
    )
    assert write_res["ok"] is True
    assert write_res["bytes_written"] == 3
    assert adapter.serial.out_buffers["COM3"] == b"ABC"

    # Feed input to COM3 in buffer and read
    adapter.serial.in_buffers["COM3"] = bytearray(b"XYZ")
    read_res = await adapter.invoke(
        "peripheral.serial.read", "1.0.0", {"port": "COM3", "max_bytes": 10}
    )
    assert read_res["ok"] is True
    assert read_res["bytes_read"] == 3
    assert read_res["data_hex"] == b"XYZ".hex()


async def test_sensor_telemetry_read(adapter: PeripheralAdapter):
    res = await adapter.invoke(
        "peripheral.sensor.read",
        "1.0.0",
        {"sensor_id": "environment_1", "metric_types": ["temperature_c", "humidity_pct"]},
    )
    assert res["ok"] is True
    assert "temperature_c" in res["metrics"]
    assert "humidity_pct" in res["metrics"]
    assert res["metrics"]["temperature_c"] == 22.4


async def test_camera_frame_capture(adapter: PeripheralAdapter):
    res = await adapter.invoke(
        "camera.capture",
        "1.0.0",
        {"device_id": "cam_front", "resolution": [1280, 720], "format": "jpeg"},
    )
    assert res["ok"] is True
    assert res["device_id"] == "cam_front"
    assert res["resolution"] == (1280, 720)
    assert len(res["frame_sha256"]) == 64


async def test_effect_envelope_peripheral_execution(adapter: PeripheralAdapter):
    registry = CapabilityRegistry.seed_m1_defaults()
    binding = ProviderBinding(
        meta=ProviderMeta(
            provider_id="peripheral.default",
            version="1.0.0",
            commit=None,
            license="MIT",
            license_compatibility="approved",
            adapter="jarvis.adapters.peripherals",
            trust_level="sandboxed",
            process_model="subprocess",
            network="none",
            health_check="peripheral: probe",
            cve_status="checked_clean",
            last_audit_utc="2026-09-24T00:00:00Z",
            provenance_added_by="creator",
            provenance_added_at_utc="2026-09-24T00:00:00Z",
            provenance_reason="M5.4 peripheral control",
            fallback_provider_id=None,
        ),
        contracts=[
            ContractDef(
                contract_id="peripheral.gpio.write",
                version="1.0.0",
                args_schema={"pin": {"type": "integer"}, "value": {"type": "integer"}},
            )
        ],
    )
    registry.register_provider("creator", binding)

    engine = EffectEnvelopeEngine(registry, {"peripheral.default": adapter})

    manifest = Manifest(
        manifest_id="manifest-peripheral-1",
        intent_id="intent-gpio-1",
        contracts=[
            ResolvedContract(
                id="peripheral.gpio.write",
                version="1.0.0",
                args={"pin": 21, "value": 1},
            )
        ],
        required_capabilities=["peripheral.gpio.write"],
        budget=Budget(),
        constraints={},
        risk_class="safe",
        manifest_sha256="0" * 64,
        created_at_utc="2026-09-24T20:00:00Z",
    )

    envelope = await engine.run(
        manifest,
        "peripheral.gpio.write",
        intended_change={"pin": 21, "value": 1},
        postconditions={"ok": True, "pin": 21, "value": 1},
        idempotency_key="k-gpio-write-21",
    )

    assert isinstance(envelope, EffectEnvelope)
    assert envelope.verification.passed is True
    assert envelope.provider_id == "peripheral.default"
    assert envelope.contract_id == "peripheral.gpio.write"
    assert adapter.gpio.pin_states[21] == 1
