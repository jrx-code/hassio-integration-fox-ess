"""Config flow for FoxESS inverters."""

from __future__ import annotations

import logging
from typing import Any

from foxess_modbus import FoxEssH3Inverter, UnsupportedModelError
from modbus_connection import ModbusError, ModbusTcpParams
import voluptuous as vol

from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import CONF_UNIT_ID, DEFAULT_PORT, DEFAULT_UNIT_ID, DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(),
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=65535)
            ),
            vol.Coerce(int),
        ),
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(
            NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=247)
            ),
            vol.Coerce(int),
        ),
    }
)


async def _async_probe(hass: HomeAssistant, data: dict[str, Any]) -> str:
    """Read the inverter's identity; return its model name, or raise."""
    params = ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT])
    async with async_get_temporary_unit(hass, params, data[CONF_UNIT_ID]) as unit:
        device = FoxEssH3Inverter(unit)
        await device.async_ensure_setup()
    assert device.model is not None
    return device.model.name


class FoxEssConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a FoxESS config flow.

    The H3 reports no serial number over Modbus, so an entry is keyed by its
    link (host, port, unit id) instead of a unique id.
    """

    VERSION = 1

    async def _async_validate(
        self, user_input: dict[str, Any]
    ) -> tuple[str | None, dict[str, str], dict[str, str]]:
        """Probe the inverter. Return its model, the errors and placeholders."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        try:
            model = await _async_probe(self.hass, user_input)
        except UnsupportedModelError as err:
            errors["base"] = "unsupported_model"
            placeholders["model"] = err.model
        except (ModbusError, HomeAssistantError) as err:
            _LOGGER.debug("Probing %s failed: %s", user_input[CONF_HOST], err)
            errors["base"] = "cannot_connect"
            placeholders["error"] = str(err)
        else:
            return model, errors, placeholders
        return None, errors, placeholders

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the gateway and the inverter's unit id."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match(
                {
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                    CONF_UNIT_ID: user_input[CONF_UNIT_ID],
                }
            )
            model, errors, placeholders = await self._async_validate(user_input)
            if model is not None:
                return self.async_create_entry(
                    title=f"{MANUFACTURER} {model}", data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the gateway address or unit id of an existing inverter."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            model, errors, placeholders = await self._async_validate(user_input)
            if model is not None:
                return self.async_update_reload_and_abort(
                    entry, data_updates=user_input
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input or entry.data
            ),
            errors=errors,
            description_placeholders=placeholders,
        )
