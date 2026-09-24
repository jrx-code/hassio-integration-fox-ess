"""Write a setting and turn a failure into an action error."""

from __future__ import annotations

from typing import Any

from modbus_connection import ModbusError

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import DOMAIN
from .coordinator import FoxEssCoordinator


async def async_write_setting(
    coordinator: FoxEssCoordinator, field: str, value: Any
) -> None:
    """Write one settings field, then read the settings back."""
    try:
        await coordinator.device.settings.write(field, value)
    except ValueError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_value",
            translation_placeholders={"value": str(value), "error": str(err)},
        ) from err
    except ModbusError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="write_failed",
            translation_placeholders={"error": str(err)},
        ) from err
    await coordinator.async_request_refresh()
