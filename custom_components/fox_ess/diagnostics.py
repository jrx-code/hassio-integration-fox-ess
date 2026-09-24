"""Diagnostics for FoxESS inverters."""

from __future__ import annotations

from typing import Any

from modbus_connection import ModbusError

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import FoxEssConfigEntry

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FoxEssConfigEntry
) -> dict[str, Any]:
    """The raw register map, for a bug report or a regression test."""
    runtime_data = entry.runtime_data
    device = runtime_data.device
    identity = device.identity
    try:
        registers: dict[str, Any] = dict(await device.async_read_raw())
    except ModbusError as err:
        registers = {"error": str(err)}

    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "model": identity.model,
        "master_version": str(identity.master_version),
        "slave_version": str(identity.slave_version),
        "manager_version": str(identity.manager_version),
        "bms": device.bms is not None,
        "battery_today_valid": device.energy.battery_today_valid,
        "active_faults": device.inverter.active_faults,
        "readings": {
            "updated": sorted(runtime_data.readings.data.updated),
            "failed": {k: str(v) for k, v in runtime_data.readings.data.failed.items()},
        },
        "settings": {
            "updated": sorted(runtime_data.settings.data.updated),
            "failed": {k: str(v) for k, v in runtime_data.settings.data.failed.items()},
        },
        "registers": registers,
    }
