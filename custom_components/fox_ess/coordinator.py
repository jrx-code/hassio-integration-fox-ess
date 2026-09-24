"""Data update coordinators for FoxESS inverters."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
import logging

from foxess_modbus import FoxEssH3Inverter, UnsupportedModelError, UpdateReport
from modbus_connection import ModbusError, ModbusTimeoutError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, MANUFACTURER, TIMEOUTS_BEFORE_DISCONNECT

_LOGGER = logging.getLogger(__name__)


@dataclass
class FoxEssRuntimeData:
    """What a loaded entry holds."""

    readings: FoxEssCoordinator
    settings: FoxEssCoordinator

    @property
    def device(self) -> FoxEssH3Inverter:
        """The inverter both coordinators poll."""
        return self.readings.device

    def coordinator_for(self, report: str) -> FoxEssCoordinator:
        """The coordinator whose poll covers a sub-system."""
        return self.settings if report == "settings" else self.readings


type FoxEssConfigEntry = ConfigEntry[FoxEssRuntimeData]


class FoxEssCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Run one of the inverter's update methods on its own interval."""

    config_entry: FoxEssConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: FoxEssConfigEntry,
        device: FoxEssH3Inverter,
        poll: Callable[[], Awaitable[UpdateReport]],
        interval: timedelta,
        *,
        recycles_link: bool = False,
    ) -> None:
        """Initialize the coordinator.

        Only the coordinator on the fastest interval sets ``recycles_link``,
        so a second one never drops the link under a poll in flight.
        """
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{entry.title} {poll.__name__}",
            update_interval=interval,
        )
        self.device = device
        self._poll = poll
        self._recycles_link = recycles_link
        self._timeouts = 0
        self._failed: frozenset[str] = frozenset()

    async def _async_update_data(self) -> UpdateReport:
        try:
            report = await self._poll()
        except UnsupportedModelError as err:
            # The inverter was swapped for another model: nothing to retry.
            raise ConfigEntryError(
                translation_domain=DOMAIN,
                translation_key="unsupported_model",
                translation_placeholders={"model": err.model},
            ) from err
        except ModbusTimeoutError as err:
            self._timeouts += 1
            if self._recycles_link and self._timeouts >= TIMEOUTS_BEFORE_DISCONNECT:
                # A gateway can keep the socket open while the inverter behind
                # it stopped answering; a fresh link is the only way out.
                self._timeouts = 0
                await self.device.modbus_unit.disconnect()
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="modbus_error",
                translation_placeholders={"error": str(err)},
            ) from err
        except ModbusError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="modbus_error",
                translation_placeholders={"error": str(err)},
            ) from err
        self._timeouts = 0

        if not report.updated:
            errors = list(report.failed.values())
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="no_component_answered",
            ) from ExceptionGroup("every sub-system failed", errors)

        for name in sorted(report.failed.keys() - self._failed):
            _LOGGER.warning(
                "%s: %s failed to refresh: %s", self.name, name, report.failed[name]
            )
        for name in sorted(self._failed - report.failed.keys()):
            _LOGGER.info("%s: %s is available again", self.name, name)
        self._failed = frozenset(report.failed)
        return report

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Describe the inverter to the registry."""
        identity = self.device.identity
        model = self.device.model
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=model.name if model else identity.model,
            sw_version=(
                f"Master {identity.master_version} / "
                f"Slave {identity.slave_version} / "
                f"Manager {identity.manager_version}"
            ),
        )
