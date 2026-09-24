"""Tests for the FoxESS integration."""

from modbus_connection.mock import MockModbusUnit

from custom_components.fox_ess.const import CONF_UNIT_ID
from homeassistant.const import CONF_HOST, CONF_PORT

MOCK_USER_INPUT = {CONF_HOST: "192.0.2.10", CONF_PORT: 502, CONF_UNIT_ID: 247}
MOCK_MODEL = "H3-10.0-E"


def _chars(text: str, length: int) -> list[int]:
    return [ord(c) for c in text.ljust(length, "\0")[:length]]


def _s16(value: int) -> int:
    return value & 0xFFFF


def seed_h3(unit: MockModbusUnit, *, manager: int = 0x195) -> None:
    """Seed an H3-10.0-E, by default on manager firmware 1.95."""
    unit.holding.update(
        {
            30000: _chars(f"   {MOCK_MODEL}", 15),
            30016: [223, 103, manager],
            31000: [4520, 36, 1540, 3100, 5, _s16(-2)],
            31006: [2301, 2299, 2305, 45, 44, 46, 1000, 1010, 990, 5001],
            31022: [0, 0, 0, 0, _s16(-500), 200, 100, 800, 700, 600],
            31032: [452, 301, 4103, _s16(-18), _s16(-730), 215, 93],
            31041: 3,
            31044: [0] * 8,
            31090: 99,
            31123: 1234,
            32000: [0, 50000, 123, 1, 32669, 190, 1, 26432, 54],
            32009: [0, 29931, 45, 2, 37608, 12],
            32021: [4, 47298, 150],
            41000: 0,
            41007: [260, 250, 10, 100, 10],
        }
    )
