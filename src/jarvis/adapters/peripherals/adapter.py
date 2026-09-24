from __future__ import annotations

"""Peripheral Provider Adapter implementation (src/jarvis/adapters/peripherals/adapter.py).

Implements ProviderAdapter protocol exposing:
- peripheral.gpio.write
- peripheral.gpio.read
- peripheral.gpio.pwm
- peripheral.sensor.read
- peripheral.serial.write
- peripheral.serial.read
- camera.capture
"""

from typing import Any, Mapping

from jarvis.adapters.peripherals.drivers import (
    MockCameraDriver,
    MockGPIODriver,
    MockSensorDriver,
    MockSerialDriver,
)
from jarvis.adapters.peripherals.jails import GPIOPinJail, SerialPortJail


class PeripheralAdapter:
    """Hardware peripheral adapter satisfying the ProviderAdapter protocol."""

    def __init__(
        self,
        gpio_driver: MockGPIODriver | None = None,
        sensor_driver: MockSensorDriver | None = None,
        serial_driver: MockSerialDriver | None = None,
        camera_driver: MockCameraDriver | None = None,
        pin_jail: GPIOPinJail | None = None,
        port_jail: SerialPortJail | None = None,
        provider_id: str = "peripheral.default",
    ) -> None:
        self._provider_id = provider_id
        self.gpio = gpio_driver or MockGPIODriver()
        self.sensor = sensor_driver or MockSensorDriver()
        self.serial = serial_driver or MockSerialDriver()
        self.camera = camera_driver or MockCameraDriver()
        self.pin_jail = pin_jail or GPIOPinJail()
        self.port_jail = port_jail or SerialPortJail()

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def health_check(self) -> bool:
        """Peripheral adapter is healthy if drivers are initialized."""
        return True

    async def invoke(
        self,
        contract_id: str,
        version: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Dispatch hardware contracts under strict pin and port jailing."""
        if contract_id == "peripheral.gpio.write":
            pin = int(args["pin"])
            self.pin_jail.validate_pin(pin)
            value = int(args["value"])
            mode = args.get("mode", "out")
            return self.gpio.write_pin(pin, value, mode=mode)

        elif contract_id == "peripheral.gpio.read":
            pin = int(args["pin"])
            self.pin_jail.validate_pin(pin)
            mode = args.get("mode", "in")
            return self.gpio.read_pin(pin, mode=mode)

        elif contract_id == "peripheral.gpio.pwm":
            pin = int(args["pin"])
            self.pin_jail.validate_pin(pin)
            duty_cycle = float(args["duty_cycle"])
            freq = float(args.get("frequency_hz", 1000.0))
            return self.gpio.set_pwm(pin, duty_cycle, freq)

        elif contract_id == "peripheral.sensor.read":
            sensor_id = args.get("sensor_id", "environment_1")
            metric_types = args.get("metric_types")
            return self.sensor.read_metrics(sensor_id, metric_types)

        elif contract_id == "peripheral.serial.write":
            port = args["port"]
            self.port_jail.validate_port(port)
            baud = int(args.get("baud_rate", 115200))
            data_hex = args["data_hex"]
            raw_bytes = bytes.fromhex(data_hex)
            return self.serial.write_bytes(port, baud, raw_bytes)

        elif contract_id == "peripheral.serial.read":
            port = args["port"]
            self.port_jail.validate_port(port)
            baud = int(args.get("baud_rate", 115200))
            max_bytes = int(args.get("max_bytes", 256))
            return self.serial.read_bytes(port, baud, max_bytes)

        elif contract_id == "camera.capture":
            device_id = args.get("device_id", "cam0")
            resolution = tuple(args.get("resolution", (640, 480)))
            fmt = args.get("format", "jpeg")
            return self.camera.capture_frame(device_id, resolution, fmt)

        raise ValueError(
            f"Unsupported contract '{contract_id}' for provider '{self._provider_id}'"
        )
