"""Entry setup, unload and the coordinators."""

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from modbus_connection import IllegalDataAddressError, ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.fox_ess.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from . import _chars


async def test_setup_and_unload(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    assert init_integration.state is ConfigEntryState.LOADED
    [device] = dr.async_entries_for_config_entry(
        device_registry, init_integration.entry_id
    )
    assert device.identifiers == {(DOMAIN, init_integration.entry_id)}
    assert device.manufacturer == "FoxESS"
    assert device.model == "H3-10.0-E"
    assert device.sw_version == "Master 2.23 / Slave 1.03 / Manager 1.95"

    assert await hass.config_entries.async_unload(init_integration.entry_id)
    assert init_integration.state is ConfigEntryState.NOT_LOADED


async def test_unreachable_is_not_ready(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_connection: MockModbusConnection,
    mock_unit: MockModbusUnit,
) -> None:
    mock_unit.fail_requests(ModbusTimeoutError())
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.fox_ess.async_get_unit",
        side_effect=lambda *args: mock_unit,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_swapped_model_is_a_setup_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_unit: MockModbusUnit,
) -> None:
    mock_unit.holding[30000] = _chars("H1-5.0-E", 15)
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.fox_ess.async_get_unit",
        side_effect=lambda *args: mock_unit,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_offline_inverter_keeps_totals(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    """At night the inverter goes quiet: measurements drop, totals hold."""
    assert (
        hass.states.get("sensor.foxess_h3_10_0_e_battery_state_of_charge").state == "93"
    )

    mock_unit.fail_requests(ModbusTimeoutError())
    freezer.tick(timedelta(seconds=11))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    soc = hass.states.get("sensor.foxess_h3_10_0_e_battery_state_of_charge")
    assert soc.state == STATE_UNAVAILABLE
    solar = hass.states.get("sensor.foxess_h3_10_0_e_solar_energy")
    assert solar.state == "5000.0"

    mock_unit.fail_requests(None)
    freezer.tick(timedelta(seconds=11))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert (
        hass.states.get("sensor.foxess_h3_10_0_e_battery_state_of_charge").state == "93"
    )


async def test_failed_subsystem_only_hits_its_entities(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    mock_unit.fail_read(31090, IllegalDataAddressError())
    freezer.tick(timedelta(seconds=11))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert (
        hass.states.get("sensor.foxess_h3_10_0_e_battery_energy_remaining").state
        == STATE_UNAVAILABLE
    )
    assert (
        hass.states.get("sensor.foxess_h3_10_0_e_battery_state_of_charge").state == "93"
    )
