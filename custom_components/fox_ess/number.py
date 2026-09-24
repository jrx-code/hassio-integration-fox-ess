"""Number entities for FoxESS inverters."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FoxEssConfigEntry
from .entity import FoxEssEntity, FoxEssEntityDescription
from .write import async_write_setting

# Writes go out one at a time over a shared serial line.
PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class FoxEssNumberDescription(NumberEntityDescription, FoxEssEntityDescription):
    """Describe a FoxESS number. ``key`` is the settings field it writes."""


def _current(key: str) -> FoxEssNumberDescription:
    return FoxEssNumberDescription(
        key=key,
        translation_key=key,
        report="settings",
        device_class=NumberDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        native_min_value=0,
        native_max_value=50,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    )


def _soc(key: str) -> FoxEssNumberDescription:
    return FoxEssNumberDescription(
        key=key,
        translation_key=key,
        report="settings",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    )


NUMBERS: tuple[FoxEssNumberDescription, ...] = (
    _current("max_charge_current"),
    _current("max_discharge_current"),
    _soc("min_soc"),
    _soc("max_soc"),
    _soc("min_soc_on_grid"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FoxEssConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FoxESS numbers."""
    async_add_entities(
        FoxEssNumber(entry.runtime_data, description) for description in NUMBERS
    )


class FoxEssNumber(FoxEssEntity, NumberEntity):
    """A battery limit the inverter keeps."""

    entity_description: FoxEssNumberDescription

    @property
    def native_value(self) -> float | None:
        """The configured value."""
        value: float | None = getattr(
            self.coordinator.device.settings, self.entity_description.key
        )
        return value

    async def async_set_native_value(self, value: float) -> None:
        """Write a new value to the inverter."""
        if self.entity_description.native_step == 1:
            await async_write_setting(
                self.coordinator, self.entity_description.key, int(value)
            )
        else:
            await async_write_setting(
                self.coordinator, self.entity_description.key, value
            )
