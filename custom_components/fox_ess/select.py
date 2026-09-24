"""Select entities for FoxESS inverters."""

from __future__ import annotations

from dataclasses import dataclass

from foxess_modbus import WorkMode

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FoxEssConfigEntry
from .entity import FoxEssEntity, FoxEssEntityDescription
from .write import async_write_setting

# Writes go out one at a time over a shared serial line.
PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class FoxEssSelectDescription(SelectEntityDescription, FoxEssEntityDescription):
    """Describe a FoxESS select."""


WORK_MODE = FoxEssSelectDescription(
    key="work_mode",
    translation_key="work_mode",
    report="settings",
    entity_category=EntityCategory.CONFIG,
    options=[mode.name.lower() for mode in WorkMode],
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FoxEssConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FoxESS selects."""
    async_add_entities([FoxEssWorkModeSelect(entry.runtime_data, WORK_MODE)])


class FoxEssWorkModeSelect(FoxEssEntity, SelectEntity):
    """The inverter's work mode."""

    entity_description: FoxEssSelectDescription

    @property
    def current_option(self) -> str | None:
        """The mode the inverter runs in."""
        mode = self.coordinator.device.settings.work_mode
        return mode.name.lower() if mode is not None else None

    async def async_select_option(self, option: str) -> None:
        """Switch the inverter to another mode."""
        await async_write_setting(
            self.coordinator, "work_mode", WorkMode[option.upper()]
        )
