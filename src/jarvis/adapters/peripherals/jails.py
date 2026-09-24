from __future__ import annotations

"""Pin and Port Jailing boundaries for hardware peripherals (src/jarvis/adapters/peripherals/jails.py).

Enforces physical safety constraints: prevents writing to reserved system pins or accessing
unauthorized communication ports.
"""

from dataclasses import dataclass, field
from typing import Sequence


class PinJailError(PermissionError):
    """Raised when a GPIO operation targets an unauthorized or reserved pin."""


class PortJailError(PermissionError):
    """Raised when a serial/communication operation targets an unauthorized port."""


class PeripheralExecutionError(RuntimeError):
    """Raised when a peripheral driver encounters a hardware or transmission error."""


@dataclass(frozen=True)
class GPIOPinJail:
    """Enforces allowed GPIO pin numbers and blocks reserved/critical system pins."""

    allowed_pins: tuple[int, ...] = tuple(range(2, 28))  # Standard BCM GPIO range
    reserved_pins: tuple[int, ...] = (0, 1, 14, 15)  # ID EEPROM and UART default console

    def validate_pin(self, pin: int) -> None:
        """Validate that a pin is within the allowed set and not reserved."""
        if pin in self.reserved_pins:
            raise PinJailError(f"Pin {pin} is a reserved system pin and cannot be modified.")
        if pin not in self.allowed_pins:
            raise PinJailError(f"Pin {pin} is outside the allowed pin jail {self.allowed_pins}.")


@dataclass(frozen=True)
class SerialPortJail:
    """Enforces allowed serial/UART/USB communication ports."""

    allowed_ports: tuple[str, ...] = ("COM3", "COM4", "/dev/ttyUSB0", "/dev/ttyACM0")

    def validate_port(self, port: str) -> None:
        """Validate that a requested serial port is explicitly whitelisted."""
        if port not in self.allowed_ports:
            raise PortJailError(
                f"Port '{port}' is not in the authorized serial port jail: {self.allowed_ports}."
            )
