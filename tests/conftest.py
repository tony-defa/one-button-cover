"""Pytest fixtures and test setup for Auto Cover integration tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Disable pytest-socket blocking (required for asyncio on Windows)
os.environ["PYTEST_DISABLE_SOCKET_CHECK"] = "1"

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_socket import disable_socket, enable_socket


def pytest_runtest_setup(item):
    """Enable sockets for all tests (required for asyncio event loops on Windows)."""
    try:
        enable_socket()
    except:
        pass  # Ignore if already enabled
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
    import threading
    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=None)
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()  # Make async_call awaitable
    hass.config_entries = MagicMock()
    # Mock methods for duplicate detection
    hass.config_entries.async_entries = MagicMock(side_effect=lambda domain=None: [])
    hass.config_entries.async_entry_for_domain_unique_id = MagicMock(return_value=None)  # No existing entry
    hass.loop = asyncio.get_event_loop()
    hass.loop_thread_id = threading.get_ident()  # Add thread ID for async_write_ha_state
    hass.bus = MagicMock()  # Add bus for event listeners
    hass.bus.async_listen = MagicMock(return_value=lambda: None)  # Return a removal function
    hass.helpers = MagicMock()  # Add helpers for entity validation
    hass.helpers.entity_registry = MagicMock()
    hass.helpers.entity_registry.async_get = AsyncMock()
    hass.data = {}
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
def auto_cover(hass, config_entry):
    """Create an AutoCover instance with proper initialization."""
    from custom_components.autocover.cover import AutoCover
    
    cover = AutoCover(
        hass=hass,
        name=config_entry.title,
        unique_id=config_entry.entry_id,
        button_entity=config_entry.data[CONF_BUTTON_ENTITY],
        time_to_open=config_entry.data[CONF_TIME_TO_OPEN],
        time_to_close=config_entry.data[CONF_TIME_TO_CLOSE],
        closed_sensor=config_entry.data.get(CONF_CLOSED_SENSOR),
        open_sensor=config_entry.data.get(CONF_OPEN_SENSOR),
        threshold=config_entry.data.get(CONF_THRESHOLD, 10),
    )
    # Set entity_id to avoid NoEntitySpecifiedError
    cover.entity_id = f"cover.{config_entry.entry_id}"
    # Mock platform to avoid entity registry warnings
    cover.platform = MagicMock()
    return cover


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
    # Set up async_get to accept entity_id and return proper mock or None
    def mock_async_get(entity_id):
        # Return a mock entity for test entities, None for nonexistent ones
        if entity_id in ["button.test_button", "binary_sensor.open_sensor", "binary_sensor.closed_sensor"]:
            mock_entity = MagicMock()
            mock_entity.entity_id = entity_id
            return mock_entity
        return None
    
    registry.async_get = mock_async_get
    # Add _entities_data attribute for compatibility
    registry._entities_data = {}
    # Add entities attribute
    registry.entities = MagicMock()
    registry.entities.get_entry = MagicMock(return_value=None)
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
    # Enable socket before creating event loop (required for Windows)
    try:
        enable_socket()
    except:
        pass
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
    # Create a proper mock entity registry
    registry = MagicMock(spec=er.EntityRegistry)
    registry._entities_data = {}
    registry.entities = MagicMock()
    registry.entities.get_entry = MagicMock(return_value=None)
    
    # Set up async_get to return proper mocks for test entities
    def mock_async_get_method(entity_id):
        if entity_id in ["button.test_button", "binary_sensor.open_sensor", "binary_sensor.closed_sensor", "button.garage_door_opener"]:
            mock_entity = MagicMock()
            mock_entity.entity_id = entity_id
            return mock_entity
        return None
    
    registry.async_get = mock_async_get_method
    
    # Patch both the function and where it's imported in config_flow
    with patch("homeassistant.helpers.entity_registry.async_get", return_value=registry):
        with patch("custom_components.autocover.config_flow.async_get_entity_registry", return_value=registry):
            yield registry


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