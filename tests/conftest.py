"""Fixtures for the FoxESS integration tests."""

from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from modbus_connection import ModbusTcpParams
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fox_ess.const import DOMAIN
from homeassistant.core import HomeAssistant

from . import MOCK_MODEL, MOCK_USER_INPUT, seed_h3


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load custom_components/ in every test."""


@pytest.fixture
def mock_connection() -> MockModbusConnection:
    """A gateway with an H3 at unit 247."""
    connection = MockModbusConnection()
    seed_h3(connection.for_unit(247))
    return connection


@pytest.fixture
def mock_unit(mock_connection: MockModbusConnection) -> MockModbusUnit:
    """The H3 on the mock gateway."""
    return mock_connection.for_unit(247)


@pytest.fixture
def mock_temporary_unit(
    mock_connection: MockModbusConnection,
) -> Generator[None]:
    """Hand the config flow units on the mock gateway."""

    @asynccontextmanager
    async def _get(
        hass: HomeAssistant, params: ModbusTcpParams, unit_id: int
    ) -> AsyncIterator[MockModbusUnit]:
        yield mock_connection.for_unit(unit_id)

    with patch(
        "custom_components.fox_ess.config_flow.async_get_temporary_unit",
        side_effect=_get,
    ):
        yield


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Skip entry setup in config flow tests."""
    with patch(
        "custom_components.fox_ess.async_setup_entry", return_value=True
    ) as mock:
        yield mock


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """A config entry for the H3."""
    return MockConfigEntry(
        domain=DOMAIN, title=f"FoxESS {MOCK_MODEL}", data=MOCK_USER_INPUT
    )


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> AsyncIterator[MockConfigEntry]:
    """Set up the integration against the mock gateway."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.fox_ess.async_get_unit",
        side_effect=lambda hass, entry, params, unit_id: mock_connection.for_unit(
            unit_id
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        yield mock_config_entry
