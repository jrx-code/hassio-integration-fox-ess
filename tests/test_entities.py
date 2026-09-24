"""Sensors, the fault sensor, the work mode select and the numbers."""

from unittest.mock import patch

from modbus_connection import IllegalDataValueError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit, WriteEvent
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er

from . import seed_h3

PREFIX = "foxess_h3_10_0_e"


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize(
    ("entity", "state"),
    [
        ("pv_power", "1.54"),
        ("pv2_power", "0.0"),
        ("grid_power", "-0.2"),
        ("feed_in_power", "0.0"),
        ("grid_import_power", "0.2"),
        ("load_power", "2.1"),
        ("battery_state_of_charge", "93"),
        ("battery_charge_power", "0.73"),
        ("battery_discharge_power", "0.0"),
        ("battery_state_of_health", "99"),
        ("battery_energy_remaining", "12.34"),
        ("grid_frequency", "50.01"),
        ("solar_energy", "5000.0"),
        ("battery_charge_energy", "9820.5"),
    ],
)
async def test_sensor_states(hass: HomeAssistant, entity: str, state: str) -> None:
    assert hass.states.get(f"sensor.{PREFIX}_{entity}").state == state


@pytest.mark.usefixtures("init_integration")
async def test_battery_today_absent_on_manager_195(hass: HomeAssistant) -> None:
    assert hass.states.get(f"sensor.{PREFIX}_battery_charge_energy_today") is None


async def test_battery_today_present_before_manager_193(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    connection = MockModbusConnection()
    seed_h3(connection.for_unit(247), manager=0x192)
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.fox_ess.async_get_unit",
        side_effect=lambda hass, entry, params, unit_id: connection.for_unit(unit_id),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    assert (
        hass.states.get(f"sensor.{PREFIX}_battery_charge_energy_today").state == "19.0"
    )


@pytest.mark.usefixtures("init_integration")
async def test_disabled_by_default(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    entry = entity_registry.async_get(f"sensor.{PREFIX}_state_code")
    assert entry is not None
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


@pytest.mark.usefixtures("init_integration")
async def test_fault_sensor(hass: HomeAssistant) -> None:
    assert hass.states.get(f"binary_sensor.{PREFIX}_fault").state == "off"


@pytest.mark.usefixtures("init_integration")
async def test_select_work_mode(hass: HomeAssistant, mock_unit: MockModbusUnit) -> None:
    entity_id = f"select.{PREFIX}_work_mode"
    assert hass.states.get(entity_id).state == "self_use"

    events: list[WriteEvent] = []
    mock_unit.on_write(events.append)
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: "feed_in_first"},
        blocking=True,
    )
    assert [(e.address, e.values, e.function_code) for e in events] == [
        (41000, [1], 0x06)
    ]
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "feed_in_first"


@pytest.mark.usefixtures("init_integration")
async def test_number_min_soc_on_grid(
    hass: HomeAssistant, mock_unit: MockModbusUnit
) -> None:
    entity_id = f"number.{PREFIX}_min_state_of_charge_on_grid"
    assert hass.states.get(entity_id).state == "10"

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 15},
        blocking=True,
    )
    assert mock_unit.holding[41011] == 15
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "15"


@pytest.mark.usefixtures("init_integration")
async def test_number_charge_current(
    hass: HomeAssistant, mock_unit: MockModbusUnit
) -> None:
    entity_id = f"number.{PREFIX}_max_charge_current"
    assert hass.states.get(entity_id).state == "26.0"
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 20.5},
        blocking=True,
    )
    assert mock_unit.holding[41007] == 205


@pytest.mark.usefixtures("init_integration")
async def test_rejected_write_raises(
    hass: HomeAssistant, mock_unit: MockModbusUnit
) -> None:
    mock_unit.fail_write(41011, IllegalDataValueError())
    with pytest.raises(HomeAssistantError, match="refused"):
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: f"number.{PREFIX}_min_state_of_charge_on_grid",
                ATTR_VALUE: 20,
            },
            blocking=True,
        )


@pytest.mark.usefixtures("init_integration")
async def test_out_of_range_write_is_a_validation_error(hass: HomeAssistant) -> None:
    """HA bounds the number; the library bound is the last line for services."""
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: f"number.{PREFIX}_max_state_of_charge", ATTR_VALUE: 5},
            blocking=True,
        )
