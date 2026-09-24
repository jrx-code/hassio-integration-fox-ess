"""Base entity for FoxESS inverters."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import FoxEssCoordinator, FoxEssRuntimeData


@dataclass(frozen=True, kw_only=True)
class FoxEssEntityDescription(EntityDescription):
    """Describe an entity backed by an inverter attribute."""

    report: str
    """The sub-system name the device's UpdateReport uses, e.g. ``live``."""


class FoxEssEntity(CoordinatorEntity[FoxEssCoordinator]):
    """An entity reading one attribute off the inverter."""

    _attr_has_entity_name = True
    entity_description: FoxEssEntityDescription

    def __init__(
        self, runtime_data: FoxEssRuntimeData, description: FoxEssEntityDescription
    ) -> None:
        """Initialize the entity."""
        super().__init__(runtime_data.coordinator_for(description.report))
        self.entity_description = description
        self._attr_unique_id = (
            f"{self.coordinator.config_entry.entry_id}_{description.key}"
        )
        self._attr_device_info = runtime_data.readings.device_info

    @property
    def available(self) -> bool:
        """Whether this entity's sub-system answered the latest poll."""
        return (
            super().available
            and self.entity_description.report in self.coordinator.data.updated
        )
