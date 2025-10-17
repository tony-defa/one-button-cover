"""Tests for Auto Cover entity functionality."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.const import (
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
    ATTR_POSITION,
)
from homeassistant.core import State

from custom_components.autocover.const import (
    BUTTON_ACTIVATION_TIME,
    CONF_BUTTON_ENTITY,
    CONF_CLOSED_SENSOR,
    CONF_OPEN_SENSOR,
    CONF_THRESHOLD,
    CONF_TIME_TO_CLOSE,
    CONF_TIME_TO_OPEN,
    CoverState,
    DEBOUNCE_TIME,
    DOMAIN,
    MAX_RETRIES,
    POSITION_UPDATE_INTERVAL,
    STUCK_TIMEOUT,
)
from custom_components.autocover.cover import AutoCover, async_setup_entry


class TestAutoCoverInitialization:
    """Test cases for Auto Cover initialization."""

    async def test_auto_cover_initializes_with_correct_properties(self, hass, config_entry):
        """Test that AutoCover initializes with correct properties."""
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

        assert cover._attr_name == config_entry.title
        assert cover._attr_unique_id == config_entry.entry_id
        assert cover._button_entity == "button.test_button"
        assert cover._time_to_open == 30.0
        assert cover._time_to_close == 25.0
        assert cover._closed_sensor == "binary_sensor.closed_sensor"
        assert cover._open_sensor == "binary_sensor.open_sensor"
        assert cover._threshold == 10
        assert cover._state == CoverState.CLOSED
        assert cover._position == 0

    async def test_auto_cover_initializes_with_minimal_config(self, hass, minimal_config_entry):
        """Test that AutoCover initializes with minimal configuration."""
        cover = AutoCover(
            hass=hass,
            name=minimal_config_entry.title,
            unique_id=minimal_config_entry.entry_id,
            button_entity=minimal_config_entry.data[CONF_BUTTON_ENTITY],
            time_to_open=minimal_config_entry.data[CONF_TIME_TO_OPEN],
            time_to_close=minimal_config_entry.data[CONF_TIME_TO_CLOSE],
            closed_sensor=None,
            open_sensor=None,
            threshold=10,
        )

        assert cover._closed_sensor is None
        assert cover._open_sensor is None
        assert cover._threshold == 10

    async def test_auto_cover_has_correct_supported_features(self, hass, config_entry):
        """Test that AutoCover has correct supported features."""
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

        expected_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )
        assert cover._attr_supported_features == expected_features

    async def test_auto_cover_device_info_is_correct(self, hass, config_entry):
        """Test that AutoCover device info is correct."""
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

        device_info = cover.device_info
        assert device_info["identifiers"] == {(DOMAIN, config_entry.entry_id)}
        assert device_info["name"] == config_entry.title
        assert device_info["manufacturer"] == "Auto Cover"
        assert device_info["model"] == "Virtual Cover"
        assert device_info["sw_version"] == "1.0"


class TestAutoCoverProperties:
    """Test cases for Auto Cover properties."""

    async def test_current_cover_position_returns_correct_value(self, hass, config_entry):
        """Test that current_cover_position returns correct value."""
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

        # Set position and test
        cover._position = 75.5
        assert cover.current_cover_position == 75

        # Test with zero position
        cover._position = 0
        assert cover.current_cover_position == 0

        # Test with full position
        cover._position = 100
        assert cover.current_cover_position == 100

    async def test_is_opening_returns_correct_state(self, hass, config_entry):
        """Test that is_opening returns correct state."""
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

        cover._state = CoverState.OPENING
        assert cover.is_opening is True

        cover._state = CoverState.CLOSED
        assert cover.is_opening is False

    async def test_is_closing_returns_correct_state(self, hass, config_entry):
        """Test that is_closing returns correct state."""
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

        cover._state = CoverState.CLOSING
        assert cover.is_closing is True

        cover._state = CoverState.OPEN
        assert cover.is_closing is False

    async def test_is_closed_returns_correct_state(self, hass, config_entry):
        """Test that is_closed returns correct state."""
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

        # Test closed by position
        cover._position = 0
        cover._state = CoverState.OPEN
        assert cover.is_closed is True

        # Test closed by state
        cover._position = 50
        cover._state = CoverState.CLOSED
        assert cover.is_closed is True

        # Test not closed
        cover._position = 50
        cover._state = CoverState.OPEN
        assert cover.is_closed is False

    async def test_extra_state_attributes_returns_complete_info(self, hass, config_entry, mock_time):
        """Test that extra_state_attributes returns complete information."""
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

        # Set some state for testing
        cover._position = 75
        cover._last_direction = "UP"
        cover._obstacle_detected_count = 2
        cover._manual_operation_count = 1
        cover._disabled = False
        cover._failure_count = 0
        cover._button_press_time = mock_time

        attrs = cover.extra_state_attributes

        assert attrs["current_position"] == 75
        assert attrs["last_direction"] == "UP"
        assert attrs["operation_mode"] == "full_sensors"
        assert attrs["button_entity"] == "button.test_button"
        assert attrs["button_last_press"] == mock_time.isoformat()
        assert attrs["obstacle_detected_count"] == 2
        assert attrs["manual_operation_count"] == 1
        assert attrs["sensor_open_entity"] == "binary_sensor.open_sensor"
        assert attrs["sensor_closed_entity"] == "binary_sensor.closed_sensor"
        assert attrs["time_to_open"] == 30.0
        assert attrs["time_to_close"] == 25.0
        assert attrs["threshold_percentage"] == 10
        assert attrs["disabled"] is False
        assert attrs["failure_count"] == 0

    async def test_extra_state_attributes_with_no_sensors(self, hass, minimal_config_entry, mock_time):
        """Test extra_state_attributes when no sensors are configured."""
        cover = AutoCover(
            hass=hass,
            name=minimal_config_entry.title,
            unique_id=minimal_config_entry.entry_id,
            button_entity=minimal_config_entry.data[CONF_BUTTON_ENTITY],
            time_to_open=minimal_config_entry.data[CONF_TIME_TO_OPEN],
            time_to_close=minimal_config_entry.data[CONF_TIME_TO_CLOSE],
            closed_sensor=None,
            open_sensor=None,
            threshold=10,
        )

        attrs = cover.extra_state_attributes
        assert attrs["operation_mode"] == "no_sensors"
        assert attrs["sensor_open_entity"] is None
        assert attrs["sensor_closed_entity"] is None

    async def test_extra_state_attributes_with_single_sensor(self, hass, config_entry, mock_time):
        """Test extra_state_attributes with only one sensor configured."""
        cover = AutoCover(
            hass=hass,
            name=config_entry.title,
            unique_id=config_entry.entry_id,
            button_entity=config_entry.data[CONF_BUTTON_ENTITY],
            time_to_open=config_entry.data[CONF_TIME_TO_OPEN],
            time_to_close=config_entry.data[CONF_TIME_TO_CLOSE],
            closed_sensor=config_entry.data.get(CONF_CLOSED_SENSOR),
            open_sensor=None,  # No open sensor
            threshold=config_entry.data.get(CONF_THRESHOLD, 10),
        )

        attrs = cover.extra_state_attributes
        assert attrs["operation_mode"] == "single_sensor"
        assert attrs["sensor_open_entity"] is None
        assert attrs["sensor_closed_entity"] == "binary_sensor.closed_sensor"


class TestAutoCoverBasicOperations:
    """Test cases for basic cover operations."""

    async def test_open_cover_from_closed_state(self, hass, config_entry, mock_button_press_service, mock_time):
        """Test opening cover from closed state."""
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

        # Start in closed state
        cover._state = CoverState.CLOSED
        cover._position = 0

        await cover.async_open_cover()

        # Should transition to opening state
        assert cover._state == CoverState.OPENING
        assert cover._last_direction == "UP"
        assert cover._target_position == 100
        assert cover._movement_start_position == 0
        assert cover._movement_duration == 30.0  # time_to_open

        # Should have called button press service
        mock_button_press_service.assert_called_once()
        call_args = mock_button_press_service.call_args
        assert call_args[1]["domain"] == "button"
        assert call_args[1]["service"] == "press"
        assert call_args[1]["service_data"]["entity_id"] == "button.test_button"

    async def test_close_cover_from_open_state(self, hass, config_entry, mock_button_press_service, mock_time):
        """Test closing cover from open state."""
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

        # Start in open state
        cover._state = CoverState.OPEN
        cover._position = 100

        await cover.async_close_cover()

        # Should transition to closing state
        assert cover._state == CoverState.CLOSING
        assert cover._last_direction == "DOWN"
        assert cover._target_position == 0
        assert cover._movement_start_position == 100
        assert cover._movement_duration == 25.0  # time_to_close

    async def test_stop_cover_during_movement(self, hass, config_entry, mock_button_press_service, mock_time):
        """Test stopping cover during movement."""
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

        # Start in opening state
        cover._state = CoverState.OPENING
        cover._position = 50

        await cover.async_stop_cover()

        # Should transition to halted state
        assert cover._state == CoverState.HALTED

        # Should have called button press service
        mock_button_press_service.assert_called_once()

    async def test_stop_cover_when_not_moving_does_not_call_service(self, hass, config_entry, mock_button_press_service, mock_time):
        """Test stopping cover when not moving doesn't call button service."""
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

        # Start in halted state (not moving)
        cover._state = CoverState.HALTED
        cover._position = 50

        await cover.async_stop_cover()

        # Should not call button press service when not moving
        mock_button_press_service.assert_not_called()
        assert cover._state == CoverState.HALTED

    async def test_set_cover_position_with_valid_position(self, hass, config_entry, mock_button_press_service, mock_time):
        """Test setting cover to specific position."""
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

        # Start at position 0
        cover._state = CoverState.CLOSED
        cover._position = 0

        await cover.async_set_cover_position(position=75)

        # Should transition to opening state for upward movement
        assert cover._state == CoverState.OPENING
        assert cover._target_position == 75
        assert cover._movement_start_position == 0

        # Calculate expected duration: (75-0)/100 * 30 = 22.5
        expected_duration = (75 / 100) * 30.0
        assert cover._movement_duration == expected_duration

    async def test_set_cover_position_downward_movement(self, hass, config_entry, mock_button_press_service, mock_time):
        """Test setting cover to lower position (downward movement)."""
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

        # Start at position 100
        cover._state = CoverState.OPEN
        cover._position = 100

        await cover.async_set_cover_position(position=25)

        # Should transition to closing state for downward movement
        assert cover._state == CoverState.CLOSING
        assert cover._target_position == 25
        assert cover._movement_start_position == 100

        # Calculate expected duration: (100-25)/100 * 25 = 18.75
        expected_duration = (75 / 100) * 25.0
        assert cover._movement_duration == expected_duration

    async def test_set_cover_position_already_at_target_ignores_command(self, hass, config_entry, mock_button_press_service, mock_time):
        """Test setting cover to current position ignores command."""
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

        # Start at position 50
        cover._state = CoverState.HALTED
        cover._position = 50

        await cover.async_set_cover_position(position=50)

        # Should not change state or call service
        assert cover._state == CoverState.HALTED
        assert cover._position == 50
        mock_button_press_service.assert_not_called()

    async def test_set_cover_position_with_tolerance_ignores_close_positions(self, hass, config_entry, mock_button_press_service, mock_time):
        """Test setting cover position with tolerance ignores very close positions."""
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

        # Start at position 50
        cover._state = CoverState.HALTED
        cover._position = 50

        # Try to set to position 51 (within 2% tolerance)
        await cover.async_set_cover_position(position=51)

        # Should not change state or call service
        assert cover._state == CoverState.HALTED
        assert cover._position == 50
        mock_button_press_service.assert_not_called()


class TestAutoCoverDebouncing:
    """Test cases for command debouncing functionality."""

    async def test_rapid_commands_are_debounced(self, hass, config_entry, mock_time):
        """Test that rapid commands are debounced."""
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

        # First command should be accepted
        with patch.object(cover, "_press_button") as mock_press:
            await cover.async_open_cover()
            mock_press.assert_called_once()

        # Immediate second command should be ignored (debounced)
        with patch.object(cover, "_press_button") as mock_press:
            await cover.async_close_cover()
            mock_press.assert_not_called()

    async def test_commands_after_debounce_time_are_accepted(self, hass, config_entry, mock_time):
        """Test that commands after debounce time are accepted."""
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

        # First command
        await cover.async_open_cover()

        # Mock time to simulate debounce time passing
        with patch("custom_components.autocover.cover.datetime") as mock_dt:
            # Advance time by more than debounce time
            mock_dt.now.return_value = mock_time + timedelta(seconds=DEBOUNCE_TIME + 0.1)
            mock_dt.side_effect = lambda *args, **kwargs: (
                mock_time + timedelta(seconds=DEBOUNCE_TIME + 0.1) if args == () and kwargs == {}
                else datetime(*args, **kwargs)
            )

            # Second command should now be accepted
            with patch.object(cover, "_press_button") as mock_press:
                await cover.async_close_cover()
                mock_press.assert_called_once()

    async def test_disabled_cover_ignores_commands(self, hass, config_entry, mock_button_press_service):
        """Test that disabled cover ignores all commands."""
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

        # Disable the cover
        cover._disabled = True

        # Try all operations - they should all be ignored
        await cover.async_open_cover()
        await cover.async_close_cover()
        await cover.async_stop_cover()
        await cover.async_set_cover_position(position=50)

        # Button service should not be called
        mock_button_press_service.assert_not_called()


class TestAutoCoverStateTransitions:
    """Test cases for state transitions."""

    async def test_open_from_closing_state_stops_then_opens(self, hass, config_entry, mock_button_press_service, mock_time):
        """Test opening from closing state stops first, then opens."""
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

        # Start in closing state
        cover._state = CoverState.CLOSING
        cover._position = 75

        await cover.async_open_cover()

        # Should call button press twice (stop then open)
        assert mock_button_press_service.call_count == 2

        # Final state should be opening
        assert cover._state == CoverState.OPENING
        assert cover._last_direction == "UP"

    async def test_close_from_opening_state_stops_then_closes(self, hass, config_entry, mock_button_press_service, mock_time):
        """Test closing from opening state stops first, then closes."""
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

        # Start in opening state
        cover._state = CoverState.OPENING
        cover._position = 25

        await cover.async_close_cover()

        # Should call button press twice (stop then close)
        assert mock_button_press_service.call_count == 2

        # Final state should be closing
        assert cover._state == CoverState.CLOSING
        assert cover._last_direction == "DOWN"

    async def test_open_from_already_open_state_logs_debug(self, hass, config_entry, mock_logger, mock_time):
        """Test opening from already open state logs debug message."""
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

        # Start in open state
        cover._state = CoverState.OPEN
        cover._position = 100

        with patch.object(cover, "_press_button"):
            await cover.async_open_cover()

        # Should log debug message
        mock_logger.debug.assert_called_once_with("Cover %s is already open", config_entry.title)

    async def test_close_from_already_closed_state_logs_debug(self, hass, config_entry, mock_logger, mock_time):
        """Test closing from already closed state logs debug message."""
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

        # Start in closed state
        cover._state = CoverState.CLOSED
        cover._position = 0

        with patch.object(cover, "_press_button"):
            await cover.async_close_cover()

        # Should log debug message
        mock_logger.debug.assert_called_once_with("Cover %s is already closed", config_entry.title)


class TestAutoCoverPositionTracking:
    """Test cases for position tracking functionality."""

    async def test_position_updates_during_movement(self, hass, config_entry, mock_time):
        """Test that position updates correctly during movement."""
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

        # Start opening from position 0
        cover._position = 0
        cover._movement_start_time = mock_time
        cover._movement_start_position = 0
        cover._movement_duration = 30.0
        cover._last_direction = "UP"
        cover._state = CoverState.OPENING

        # Simulate time passing (15 seconds into 30 second movement)
        with patch("custom_components.autocover.cover.datetime") as mock_dt:
            later_time = mock_time + timedelta(seconds=15)
            mock_dt.now.return_value = later_time

            # Update position
            cover._update_position()

            # Should be at 50% (15/30 * 100)
            assert abs(cover._position - 50.0) < 0.1

    async def test_position_updates_during_closing_movement(self, hass, config_entry, mock_time):
        """Test that position updates correctly during closing movement."""
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

        # Start closing from position 100
        cover._position = 100
        cover._movement_start_time = mock_time
        cover._movement_start_position = 100
        cover._movement_duration = 25.0
        cover._last_direction = "DOWN"
        cover._state = CoverState.CLOSING

        # Simulate time passing (10 seconds into 25 second movement)
        with patch("custom_components.autocover.cover.datetime") as mock_dt:
            later_time = mock_time + timedelta(seconds=10)
            mock_dt.now.return_value = later_time

            # Update position
            cover._update_position()

            # Should be at 60% (100 - (10/25 * 100))
            expected_position = 100 - (10 / 25 * 100)
            assert abs(cover._position - expected_position) < 0.1

    async def test_partial_position_movement_calculates_correct_duration(self, hass, config_entry, mock_time):
        """Test that partial position movements calculate correct duration."""
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

        # Start at position 25, move to 75 (50% of full range)
        cover._position = 25

        with patch.object(cover, "_press_button"):
            with patch.object(cover, "_start_position_tracking"):
                with patch.object(cover, "_schedule_obstacle_check"):
                    with patch.object(cover, "_schedule_stop_at_position"):
                        await cover._start_opening(target_position=75)

        # Duration should be 50% of full open time (15 seconds)
        expected_duration = (50 / 100) * 30.0  # 15.0 seconds
        assert cover._movement_duration == expected_duration
        assert cover._target_position == 75


class TestAutoCoverButtonPress:
    """Test cases for button press functionality."""

    async def test_button_press_with_waiting_for_active_button(self, hass, config_entry, mock_button_press_service, mock_time):
        """Test button press waits for currently active button."""
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

        # Simulate button currently being pressed
        cover._button_pressing = True
        cover._button_press_time = mock_time

        # Mock asyncio.sleep to verify it's called
        with patch("asyncio.sleep") as mock_sleep:
            await cover._press_button()

            # Should wait for button to be available
            mock_sleep.assert_called_once()
            # Wait time should be approximately BUTTON_ACTIVATION_TIME
            wait_time = mock_sleep.call_args[0][0]
            assert wait_time >= BUTTON_ACTIVATION_TIME

    async def test_button_press_resets_failure_count_on_success(self, hass, config_entry, mock_button_press_service):
        """Test that successful button press resets failure count."""
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

        # Simulate previous failures
        cover._failure_count = 2

        await cover._press_button()

        # Failure count should be reset on success
        assert cover._failure_count == 0
        assert cover._button_pressing is True

    async def test_button_press_handles_service_call_failure(self, hass, config_entry, mock_button_press_service):
        """Test that button press handles service call failure."""
        # Mock service call to raise exception
        mock_button_press_service.side_effect = Exception("Service call failed")

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

        await cover._press_button()

        # Failure count should increase
        assert cover._failure_count == 1
        assert cover._button_pressing is False

    async def test_button_press_disables_cover_after_max_retries(self, hass, config_entry, mock_button_press_service, mock_logger):
        """Test that cover is disabled after maximum retry attempts."""
        # Mock service call to always fail
        mock_button_press_service.side_effect = Exception("Service call failed")

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

        # Simulate reaching max retries
        cover._failure_count = MAX_RETRIES - 1

        await cover._press_button()

        # Cover should be disabled
        assert cover._disabled is True
        assert cover._failure_count == MAX_RETRIES

        # Should log error about disabling
        mock_logger.error.assert_called_once_with(
            "Cover %s disabled after %d consecutive failures",
            config_entry.title,
            MAX_RETRIES,
        )


class TestAutoCoverStateRestoration:
    """Test cases for state restoration after restart."""

    async def test_state_restoration_from_open_state(self, hass, config_entry, mock_time):
        """Test state restoration from open state."""
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

        # Mock last state as open
        last_state = MagicMock(spec=State)
        last_state.state = STATE_OPEN
        last_state.attributes = {
            "current_position": 100,
            "last_direction": "UP",
            "obstacle_detected_count": 0,
            "manual_operation_count": 0,
        }

        # Mock async_get_last_state
        with patch.object(cover, "async_get_last_state", return_value=last_state):
            await cover.async_added_to_hass()

        # Should restore open state
        assert cover._state == CoverState.OPEN
        assert cover._position == 100
        assert cover._last_direction == "UP"
        assert cover._obstacle_detected_count == 0
        assert cover._manual_operation_count == 0

    async def test_state_restoration_from_opening_state_converts_to_halted(self, hass, config_entry, mock_time, mock_logger):
        """Test that opening/closing state is converted to halted on restoration."""
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

        # Mock last state as opening
        last_state = MagicMock(spec=State)
        last_state.state = STATE_OPENING
        last_state.attributes = {
            "current_position": 75,
        }

        with patch.object(cover, "async_get_last_state", return_value=last_state):
            await cover.async_added_to_hass()

        # Should convert to halted state but keep position
        assert cover._state == CoverState.HALTED
        assert cover._position == 75

        # Should log the state conversion
        mock_logger.info.assert_called_once()

    async def test_state_restoration_with_no_previous_state_defaults_to_closed(self, hass, config_entry, mock_time):
        """Test that missing previous state defaults to closed."""
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

        # Mock no last state
        with patch.object(cover, "async_get_last_state", return_value=None):
            await cover.async_added_to_hass()

        # Should default to closed state
        assert cover._state == CoverState.CLOSED
        assert cover._position == 0


class TestAutoCoverLifecycle:
    """Test cases for entity lifecycle management."""

    async def test_added_to_hass_registers_sensor_listeners(self, hass, config_entry, mock_time):
        """Test that added_to_hass registers sensor state change listeners."""
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

        with patch.object(cover, "async_get_last_state", return_value=None):
            with patch.object(cover, "_sync_position_from_sensors"):
                with patch("custom_components.autocover.cover.async_track_state_change_event") as mock_track:
                    await cover.async_added_to_hass()

                    # Should register listeners for both sensors
                    assert mock_track.call_count == 2

    async def test_added_to_hass_with_no_sensors_registers_no_listeners(self, hass, minimal_config_entry, mock_time):
        """Test that added_to_hass with no sensors registers no listeners."""
        cover = AutoCover(
            hass=hass,
            name=minimal_config_entry.title,
            unique_id=minimal_config_entry.entry_id,
            button_entity=minimal_config_entry.data[CONF_BUTTON_ENTITY],
            time_to_open=minimal_config_entry.data[CONF_TIME_TO_OPEN],
            time_to_close=minimal_config_entry.data[CONF_TIME_TO_CLOSE],
            closed_sensor=None,
            open_sensor=None,
            threshold=10,
        )

        with patch.object(cover, "async_get_last_state", return_value=None):
            with patch.object(cover, "_sync_position_from_sensors"):
                with patch("custom_components.autocover.cover.async_track_state_change_event") as mock_track:
                    await cover.async_added_to_hass()

                    # Should not register any listeners
                    mock_track.assert_not_called()

    async def test_will_remove_from_hass_cleans_up_resources(self, hass, config_entry):
        """Test that will_remove_from_hass cleans up all resources."""
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

        # Set up some resources that need cleanup
        cover._position_update_handle = MagicMock()
        cover._obstacle_check_handle = MagicMock()
        cover._sensor_listeners = [MagicMock(), MagicMock()]

        await cover.async_will_remove_from_hass()

        # Should cancel all handles
        cover._position_update_handle.assert_called_once()
        cover._obstacle_check_handle.assert_called_once()

        # Should remove all sensor listeners
        for listener in cover._sensor_listeners:
            listener.assert_called_once()

        # Should clear listener list
        assert cover._sensor_listeners == []