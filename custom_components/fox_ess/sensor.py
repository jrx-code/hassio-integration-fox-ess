"""Sensors for FoxESS inverters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from foxess_modbus import FoxEssH3Inverter

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FoxEssConfigEntry
from .entity import FoxEssEntity, FoxEssEntityDescription

PARALLEL_UPDATES = 0

type SensorValue = float | int | None


@dataclass(frozen=True, kw_only=True)
class FoxEssSensorDescription(SensorEntityDescription, FoxEssEntityDescription):
    """Describe a FoxESS sensor."""

    value_fn: Callable[[FoxEssH3Inverter], SensorValue]
    exists_fn: Callable[[FoxEssH3Inverter], bool] = lambda _: True


def _nonnegative(value: float | None) -> float | None:
    """A small negative reading (sensor noise at night) shows as 0."""
    return None if value is None else max(value, 0.0)


def _power(
    key: str,
    value_fn: Callable[[FoxEssH3Inverter], SensorValue],
    *,
    enabled: bool = True,
) -> FoxEssSensorDescription:
    return FoxEssSensorDescription(
        key=key,
        translation_key=key,
        report="live",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=3,
        entity_registry_enabled_default=enabled,
        value_fn=value_fn,
    )


def _voltage(
    key: str,
    value_fn: Callable[[FoxEssH3Inverter], SensorValue],
    *,
    enabled: bool = True,
) -> FoxEssSensorDescription:
    return FoxEssSensorDescription(
        key=key,
        translation_key=key,
        report="live",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_enabled_default=enabled,
        value_fn=value_fn,
    )


def _current(
    key: str,
    value_fn: Callable[[FoxEssH3Inverter], SensorValue],
    *,
    enabled: bool = True,
) -> FoxEssSensorDescription:
    return FoxEssSensorDescription(
        key=key,
        translation_key=key,
        report="live",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        entity_registry_enabled_default=enabled,
        value_fn=value_fn,
    )


def _temperature(
    key: str,
    report: str,
    value_fn: Callable[[FoxEssH3Inverter], SensorValue],
    *,
    enabled: bool = True,
) -> FoxEssSensorDescription:
    return FoxEssSensorDescription(
        key=key,
        translation_key=key,
        report=report,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=enabled,
        value_fn=value_fn,
    )


def _energy(
    key: str,
    value_fn: Callable[[FoxEssH3Inverter], SensorValue],
    *,
    enabled: bool = True,
    exists_fn: Callable[[FoxEssH3Inverter], bool] = lambda _: True,
) -> FoxEssSensorDescription:
    return FoxEssSensorDescription(
        key=key,
        translation_key=key,
        report="energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        entity_registry_enabled_default=enabled,
        value_fn=value_fn,
        exists_fn=exists_fn,
    )


def _grid_phase(field: str) -> Callable[[FoxEssH3Inverter], SensorValue]:
    """Read one per-phase field off the grid component."""

    def value(device: FoxEssH3Inverter) -> SensorValue:
        result: SensorValue = getattr(device.grid, field)
        return result

    return value


def _has_bms(device: FoxEssH3Inverter) -> bool:
    return device.bms is not None


def _battery_today_valid(device: FoxEssH3Inverter) -> bool:
    return device.energy.battery_today_valid


SENSORS: tuple[FoxEssSensorDescription, ...] = (
    # -- PV --
    _power("pv_power", lambda d: d.pv.pv_power),
    _power("pv1_power", lambda d: _nonnegative(d.pv.pv1_power)),
    _power("pv2_power", lambda d: _nonnegative(d.pv.pv2_power)),
    _voltage("pv1_voltage", lambda d: d.pv.pv1_voltage),
    _voltage("pv2_voltage", lambda d: d.pv.pv2_voltage),
    _current("pv1_current", lambda d: _nonnegative(d.pv.pv1_current)),
    _current("pv2_current", lambda d: _nonnegative(d.pv.pv2_current)),
    # -- grid --
    _power("grid_power", lambda d: d.grid.ct_power),
    _power("feed_in_power", lambda d: d.grid.feed_in_power),
    _power("grid_import_power", lambda d: d.grid.grid_import_power),
    _power("load_power", lambda d: d.grid.load_power),
    _power("inverter_power", lambda d: d.grid.inverter_power),
    _power("eps_power", lambda d: d.grid.eps_power, enabled=False),
    *(_power(f"grid_power_{p}", _grid_phase(f"ct_power_{p}")) for p in "rst"),
    *(
        _power(
            f"load_power_{p}",
            _grid_phase(f"load_power_{p}"),
            enabled=False,
        )
        for p in "rst"
    ),
    *(
        _power(
            f"inverter_power_{p}",
            _grid_phase(f"inverter_power_{p}"),
            enabled=False,
        )
        for p in "rst"
    ),
    *(
        _voltage(
            f"grid_voltage_{p}",
            _grid_phase(f"grid_voltage_{p}"),
        )
        for p in "rst"
    ),
    *(
        _current(
            f"inverter_current_{p}",
            _grid_phase(f"inverter_current_{p}"),
            enabled=False,
        )
        for p in "rst"
    ),
    FoxEssSensorDescription(
        key="grid_frequency",
        translation_key="grid_frequency",
        report="live",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        suggested_display_precision=2,
        value_fn=lambda d: d.grid.grid_frequency,
    ),
    # -- battery --
    FoxEssSensorDescription(
        key="battery_soc",
        translation_key="battery_soc",
        report="live",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.battery.battery_soc,
    ),
    _power("battery_power", lambda d: d.battery.battery_power),
    _power("battery_charge_power", lambda d: d.battery.battery_charge_power),
    _power("battery_discharge_power", lambda d: d.battery.battery_discharge_power),
    _voltage("battery_voltage", lambda d: d.battery.battery_voltage),
    _current("battery_current", lambda d: d.battery.battery_current),
    _temperature(
        "battery_temperature", "live", lambda d: d.battery.battery_temperature
    ),
    # -- inverter --
    _temperature(
        "inverter_temperature", "live", lambda d: d.inverter.inverter_temperature
    ),
    _temperature(
        "ambient_temperature", "live", lambda d: d.inverter.ambient_temperature
    ),
    FoxEssSensorDescription(
        key="state_code",
        translation_key="state_code",
        report="live",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.inverter.state_code,
    ),
    # -- BMS --
    FoxEssSensorDescription(
        key="battery_soh",
        translation_key="battery_soh",
        report="bms",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.bms.battery_soh if d.bms else None,
        exists_fn=_has_bms,
    ),
    FoxEssSensorDescription(
        key="battery_energy_remaining",
        translation_key="battery_energy_remaining",
        report="bms",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: d.bms.energy_remaining if d.bms else None,
        exists_fn=_has_bms,
    ),
    FoxEssSensorDescription(
        key="cell_temperature_high",
        translation_key="cell_temperature_high",
        report="bms",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.bms.cell_temperature_high if d.bms else None,
        exists_fn=_has_bms,
    ),
    FoxEssSensorDescription(
        key="cell_temperature_low",
        translation_key="cell_temperature_low",
        report="bms",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.bms.cell_temperature_low if d.bms else None,
        exists_fn=_has_bms,
    ),
    FoxEssSensorDescription(
        key="cell_voltage_high",
        translation_key="cell_voltage_high",
        report="bms",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.bms.cell_voltage_high if d.bms else None,
        exists_fn=_has_bms,
    ),
    FoxEssSensorDescription(
        key="cell_voltage_low",
        translation_key="cell_voltage_low",
        report="bms",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.bms.cell_voltage_low if d.bms else None,
        exists_fn=_has_bms,
    ),
    # -- energy --
    _energy("solar_energy_total", lambda d: d.energy.solar_total),
    _energy("solar_energy_today", lambda d: d.energy.solar_today),
    _energy("battery_charge_total", lambda d: d.energy.battery_charge_total),
    _energy(
        "battery_charge_today",
        lambda d: d.energy.battery_charge_today,
        exists_fn=_battery_today_valid,
    ),
    _energy("battery_discharge_total", lambda d: d.energy.battery_discharge_total),
    _energy(
        "battery_discharge_today",
        lambda d: d.energy.battery_discharge_today,
        exists_fn=_battery_today_valid,
    ),
    _energy("feed_in_total", lambda d: d.energy.feed_in_total),
    _energy("feed_in_today", lambda d: d.energy.feed_in_today),
    _energy("grid_import_total", lambda d: d.energy.grid_import_total),
    _energy("grid_import_today", lambda d: d.energy.grid_import_today),
    _energy("load_energy_total", lambda d: d.energy.load_total),
    _energy("load_energy_today", lambda d: d.energy.load_today),
    _energy("yield_total", lambda d: d.energy.yield_total, enabled=False),
    _energy("yield_today", lambda d: d.energy.yield_today, enabled=False),
    _energy("input_energy_total", lambda d: d.energy.input_total, enabled=False),
    _energy("input_energy_today", lambda d: d.energy.input_today, enabled=False),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FoxEssConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FoxESS sensors."""
    runtime_data = entry.runtime_data
    device = runtime_data.device
    async_add_entities(
        (
            FoxEssTotalSensor
            if description.state_class is SensorStateClass.TOTAL_INCREASING
            else FoxEssSensor
        )(runtime_data, description)
        for description in SENSORS
        if description.exists_fn(device)
    )


class FoxEssSensor(FoxEssEntity, SensorEntity):
    """A measurement read off the inverter."""

    entity_description: FoxEssSensorDescription

    @property
    def native_value(self) -> SensorValue:
        """The current value."""
        return self.entity_description.value_fn(self.coordinator.device)


class FoxEssTotalSensor(FoxEssEntity, RestoreSensor):
    """An energy counter: it holds its last value while the inverter is away.

    A gap in a TOTAL_INCREASING series damages long-term statistics and the
    energy dashboard, so the counter stays available and restores across a
    restart.
    """

    entity_description: FoxEssSensorDescription

    @property
    def available(self) -> bool:
        """Always: the last value stays valid while the inverter is offline."""
        return True

    async def async_added_to_hass(self) -> None:
        """Restore the last value, then take the current one if there is one."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last.native_value
        self._process_data()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._process_data()
        super()._handle_coordinator_update()

    def _process_data(self) -> None:
        if self.entity_description.report not in self.coordinator.data.updated:
            return
        value = self.entity_description.value_fn(self.coordinator.device)
        if value is None:
            return
        last = self._attr_native_value
        # A counter dipping by under 1 % is a torn read, not a reset.
        if isinstance(last, (int, float)) and last * 0.99 <= value < last:
            return
        self._attr_native_value = value
