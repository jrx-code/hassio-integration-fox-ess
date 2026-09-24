"""The FoxESS integration: FoxESS inverters over Modbus."""

from __future__ import annotations

from foxess_modbus import FoxEssH3Inverter
from modbus_connection import ModbusTcpParams

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_UNIT_ID, READINGS_INTERVAL, SETTINGS_INTERVAL
from .coordinator import FoxEssConfigEntry, FoxEssCoordinator, FoxEssRuntimeData

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: FoxEssConfigEntry) -> bool:
    """Set up a FoxESS inverter from a config entry."""
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        entry.data[CONF_UNIT_ID],
    )
    device = FoxEssH3Inverter(unit)

    readings = FoxEssCoordinator(
        hass,
        entry,
        device,
        device.async_update_readings,
        READINGS_INTERVAL,
        recycles_link=True,
    )
    settings = FoxEssCoordinator(
        hass, entry, device, device.async_update_settings, SETTINGS_INTERVAL
    )
    # The first read also runs the device setup (identity, firmware checks).
    await readings.async_config_entry_first_refresh()
    await settings.async_config_entry_first_refresh()

    entry.runtime_data = FoxEssRuntimeData(readings, settings)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FoxEssConfigEntry) -> bool:
    """Unload a config entry. The modbus integration closes the link."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
