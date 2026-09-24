"""Diagnostics download."""

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from homeassistant.core import HomeAssistant


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
) -> None:
    result = await get_diagnostics_for_config_entry(hass, hass_client, init_integration)
    assert result["entry"]["host"] == "**REDACTED**"
    assert result["model"] == "H3-10.0-E"
    assert result["manager_version"] == "1.95"
    assert result["battery_today_valid"] is False
    assert result["readings"] == {"updated": ["bms", "energy", "live"], "failed": {}}
    assert result["registers"]["holding"]["30016"] == 223
