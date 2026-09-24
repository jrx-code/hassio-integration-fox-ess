"""Binary sensors for FoxESS inverters."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FoxEssConfigEntry
from .entity import FoxEssEntity, FoxEssEntityDescription

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class FoxEssBinarySensorDescription(
    BinarySensorEntityDescription, FoxEssEntityDescription
):
    """Describe a FoxESS binary sensor."""


FAULT = FoxEssBinarySensorDescription(
    key="fault",
    translation_key="fault",
    report="live",
    device_class=BinarySensorDeviceClass.PROBLEM,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FoxEssConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FoxESS binary sensors."""
    async_add_entities([FoxEssFaultSensor(entry.runtime_data, FAULT)])


class FoxEssFaultSensor(FoxEssEntity, BinarySensorEntity):
    """On while the inverter reports any fault; the diagnostics name them."""

    entity_description: FoxEssBinarySensorDescription

    @property
    def is_on(self) -> bool | None:
        """Whether a fault bit is set."""
        faults = self.coordinator.device.inverter.active_faults
        return None if faults is None else bool(faults)
