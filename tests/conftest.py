"""Pytest fixtures and test setup for Auto Cover integration tests."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import STATE_CLOSED, STATE_OPEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.autocover.const import (
    CONF_BUTTON_ENTITY,
    CONF_CLOSED_SENSOR,
    CONF_OPEN_SENSOR,
    CONF_THRESHOLD,
    CONF_TIME_TO_CLOSE,
    CONF_TIME_TO_OPEN,
    CoverState,
    DEFAULT_THRESHOLD,
    DOMAIN,
)


@pytest.fixture
def hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.config_entries = MagicMock()
    hass.loop = asyncio.get_event_loop()
    return hass


@pytest.fixture
def config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=config_entries.ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.title = "Test Auto Cover"
    entry.data = {
        CONF_BUTTON_ENTITY: "button.test_button",
        CONF_TIME_TO_OPEN: 30.0,
        CONF_TIME_TO_CLOSE: 25.0,
        CONF_OPEN_SENSOR: "binary_sensor.open_sensor",
        CONF_CLOSED_SENSOR: "binary_sensor.closed_sensor",
        CONF_THRESHOLD: DEFAULT_THRESHOLD,
    }
    return entry


@pytest.fixture
def minimal_config_entry():
    """Create a minimal config entry with only required fields."""
    entry = MagicMock(spec=config_entries.ConfigEntry)
    entry.entry_id = "test_minimal_entry_id"
    entry.title = "Test Auto Cover Minimal"
    entry.data = {
        CONF_BUTTON_ENTITY: "button.test_button",
        CONF_TIME_TO_OPEN: 30.0,
        CONF_TIME_TO_CLOSE: 25.0,
    }
    return entry


@pytest.fixture
def button_entity_id():
    """Return a test button entity ID."""
    return "button.test_button"


@pytest.fixture
def open_sensor_entity_id():
    """Return a test open sensor entity ID."""
    return "binary_sensor.open_sensor"


@pytest.fixture
def closed_sensor_entity_id():
    """Return a test closed sensor entity ID."""
    return "binary_sensor.closed_sensor"


@pytest.fixture
def mock_button_state():
    """Create a mock button state."""
    state = MagicMock()
    state.entity_id = "button.test_button"
    state.state = "unknown"
    state.attributes = {"friendly_name": "Test Button"}
    return state


@pytest.fixture
def mock_open_sensor_state():
    """Create a mock open sensor state."""
    state = MagicMock()
    state.entity_id = "binary_sensor.open_sensor"
    state.state = STATE_OPEN
    state.attributes = {"friendly_name": "Open Sensor"}
    return state


@pytest.fixture
def mock_closed_sensor_state():
    """Create a mock closed sensor state."""
    state = MagicMock()
    state.entity_id = "binary_sensor.closed_sensor"
    state.state = STATE_CLOSED
    state.attributes = {"friendly_name": "Closed Sensor"}
    return state


@pytest.fixture
def mock_states(hass, mock_button_state, mock_open_sensor_state, mock_closed_sensor_state):
    """Set up mock states in hass."""
    states_dict = {
        "button.test_button": mock_button_state,
        "binary_sensor.open_sensor": mock_open_sensor_state,
        "binary_sensor.closed_sensor": mock_closed_sensor_state,
    }

    hass.states.async_entity_ids.return_value = list(states_dict.keys())
    hass.states.get.side_effect = lambda entity_id: states_dict.get(entity_id)
    hass.states.__getitem__ = lambda self, entity_id: states_dict.get(entity_id)
    hass.states.__contains__ = lambda entity_id: entity_id in states_dict
    return hass


@pytest.fixture
def mock_entity_registry():
    """Create a mock entity registry."""
    registry = MagicMock(spec=er.EntityRegistry)
    registry.async_get.return_value = None  # Entity doesn't exist in registry
    return registry


@pytest.fixture
def mock_async_add_entities():
    """Create a mock async_add_entities callback."""
    return MagicMock(spec=AddEntitiesCallback)


@pytest.fixture
def mock_service_call():
    """Mock service calls."""
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_call:
        yield mock_call


@pytest.fixture
def mock_button_press_service(mock_service_call):
    """Mock button press service specifically."""
    mock_service_call.return_value = None
    return mock_service_call


@pytest.fixture
def mock_time():
    """Mock datetime.now() for consistent time-based tests."""
    fake_now = datetime(2023, 1, 1, 12, 0, 0)

    with patch("custom_components.autocover.cover.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *args, **kwargs: fake_now if args == () and kwargs == {} else datetime(*args, **kwargs)
        yield fake_now


@pytest.fixture
def cover_config_data():
    """Return standard cover configuration data for testing."""
    return {
        CONF_BUTTON_ENTITY: "button.test_button",
        CONF_TIME_TO_OPEN: 30.0,
        CONF_TIME_TO_CLOSE: 25.0,
        CONF_OPEN_SENSOR: "binary_sensor.open_sensor",
        CONF_CLOSED_SENSOR: "binary_sensor.closed_sensor",
        CONF_THRESHOLD: DEFAULT_THRESHOLD,
    }


@pytest.fixture
def cover_states():
    """Return all possible cover states for testing."""
    return [CoverState.CLOSED, CoverState.OPEN, CoverState.OPENING, CoverState.CLOSING, CoverState.HALTED]


@pytest.fixture
def position_values():
    """Return common position values for testing."""
    return [0, 25, 50, 75, 100]


@pytest.fixture
def time_durations():
    """Return time durations for testing."""
    return {
        "quick": 0.1,
        "short": 1.0,
        "normal": 30.0,
        "long": 300.0,
    }


@pytest.fixture
def threshold_values():
    """Return threshold values for testing."""
    return [0, 10, 25, 50, 100]


@pytest.fixture
def entity_registry(hass):
    """Create a mock entity registry."""
    registry = MagicMock()
    registry.async_get.return_value = None
    hass.helpers.entity_registry.async_get.return_value = registry
    return registry


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def auto_enable_ha_config(hass):
    """Auto-enable Home Assistant config for all tests."""
    hass.config = MagicMock()
    hass.config.latitude = 40.7128
    hass.config.longitude = -74.0060
    hass.config.elevation = 10
    hass.config.time_zone = "America/New_York"
    hass.config.config_dir = "/tmp"


@pytest.fixture(autouse=True)
def auto_mock_dependencies():
    """Auto-mock common dependencies for all tests."""
    with patch("homeassistant.helpers.entity_registry.async_get") as mock_er:
        mock_er.return_value = MagicMock()
        yield mock_er


@pytest.fixture
def cleanup_listeners():
    """Ensure listeners are cleaned up after each test."""
    listeners = []

    def track_listener(listener):
        listeners.append(listener)
        return listener

    with patch("homeassistant.helpers.event.async_track_state_change_event", side_effect=track_listener) as mock_track:
        yield

        # Clean up tracked listeners
        for listener in listeners:
            if hasattr(listener, '__call__'):
                try:
                    listener()
                except Exception:
                    pass  # Ignore cleanup errors


@pytest.fixture
def mock_logger():
    """Mock logger to capture log messages."""
    with patch("custom_components.autocover.cover._LOGGER") as mock_log:
        yield mock_log


@pytest.fixture
def caplog_messages(caplog):
    """Helper fixture to get logged messages."""
    return [record.message for record in caplog.records]