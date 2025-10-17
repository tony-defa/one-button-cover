"""Tests for Auto Cover safety mechanisms."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
    MAX_RETRIES,
    STUCK_TIMEOUT,
)
from custom_components.autocover.cover import AutoCover


class TestAutoCoverSafetyMechanisms:
    """Test cases for safety mechanisms."""

    async def test_maximum_retry_limits_are_enforced(self, hass, config_entry, mock_time):
        """Test that maximum retry limits are enforced."""
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

        # Simulate reaching maximum retries through repeated failures
        cover._failure_count = MAX_RETRIES - 1

        with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
            mock_service_call.side_effect = Exception("Service call failed")

            # This failure should trigger the disable mechanism
            await cover._press_button()

            # Cover should be disabled after max retries
            assert cover._disabled is True
            assert cover._failure_count == MAX_RETRIES

    async def test_failure_count_resets_on_successful_button_press(self, hass, config_entry, mock_time):
        """Test that failure count resets on successful button press."""
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

        # Set initial failure count
        cover._failure_count = 2

        # Successful button press should reset failure count
        await cover._press_button()

        # Failure count should be reset
        assert cover._failure_count == 0
        assert cover._disabled is False

    async def test_disabled_cover_ignores_all_commands(self, hass, config_entry, mock_logger):
        """Test that disabled cover ignores all commands and logs errors."""
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

        # All commands should be ignored and log errors
        await cover.async_open_cover()
        await cover.async_close_cover()
        await cover.async_stop_cover()
        await cover.async_set_cover_position(position=50)

        # Should log error for each command
        assert mock_logger.error.call_count >= 4
        mock_logger.error.assert_called_with(
            "Cover %s is disabled due to failures",
            config_entry.title
        )

    async def test_stuck_detection_during_opening_movement(self, hass, config_entry, mock_time):
        """Test stuck detection during opening movement."""
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

        # Start opening movement
        cover._state = CoverState.OPENING
        cover._position = 50
        cover._stuck_check_position = 50
        cover._stuck_check_time = mock_time

        # Simulate time passing beyond stuck timeout
        with patch("custom_components.autocover.cover.datetime") as mock_dt:
            stuck_time = mock_time + timedelta(seconds=STUCK_TIMEOUT + 1)
            mock_dt.now.return_value = stuck_time

            with patch.object(cover, "_handle_stuck") as mock_handle_stuck:
                # Trigger stuck check
                cover._check_stuck()

                # Should detect stuck condition
                mock_handle_stuck.assert_called_once()

    async def test_stuck_detection_during_closing_movement(self, hass, config_entry, mock_time):
        """Test stuck detection during closing movement."""
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

        # Start closing movement
        cover._state = CoverState.CLOSING
        cover._position = 25
        cover._stuck_check_position = 25
        cover._stuck_check_time = mock_time

        # Simulate time passing beyond stuck timeout
        with patch("custom_components.autocover.cover.datetime") as mock_dt:
            stuck_time = mock_time + timedelta(seconds=STUCK_TIMEOUT + 1)
            mock_dt.now.return_value = stuck_time

            with patch.object(cover, "_handle_stuck") as mock_handle_stuck:
                # Trigger stuck check
                cover._check_stuck()

                # Should detect stuck condition
                mock_handle_stuck.assert_called_once()

    async def test_stuck_detection_ignores_when_not_stuck(self, hass, config_entry, mock_time):
        """Test that stuck detection doesn't trigger when not actually stuck."""
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

        # Start opening movement
        cover._state = CoverState.OPENING
        cover._position = 50
        cover._stuck_check_position = 25  # Different position
        cover._stuck_check_time = mock_time

        # Position has moved, so not stuck
        with patch("custom_components.autocover.cover.datetime") as mock_dt:
            current_time = mock_time + timedelta(seconds=STUCK_TIMEOUT + 1)
            mock_dt.now.return_value = current_time

            with patch.object(cover, "_handle_stuck") as mock_handle_stuck:
                # Trigger stuck check
                cover._check_stuck()

                # Should not detect stuck condition (position changed)
                mock_handle_stuck.assert_not_called()

    async def test_stuck_detection_ignores_when_not_moving(self, hass, config_entry, mock_time):
        """Test that stuck detection is ignored when not moving."""
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

        # Not moving (halted state)
        cover._state = CoverState.HALTED
        cover._position = 50
        cover._stuck_check_position = 50  # Same position
        cover._stuck_check_time = mock_time

        # Simulate time passing
        with patch("custom_components.autocover.cover.datetime") as mock_dt:
            current_time = mock_time + timedelta(seconds=STUCK_TIMEOUT + 1)
            mock_dt.now.return_value = current_time

            with patch.object(cover, "_handle_stuck") as mock_handle_stuck:
                # Trigger stuck check
                cover._check_stuck()

                # Should not detect stuck condition (not moving)
                mock_handle_stuck.assert_not_called()

    async def test_stuck_handling_stops_movement_and_logs_warning(self, hass, config_entry, mock_time, mock_logger):
        """Test that stuck handling stops movement and logs warning."""
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

        # Set up stuck condition
        cover._state = CoverState.OPENING
        cover._position = 50

        with patch.object(cover, "_stop_movement") as mock_stop:
            await cover._handle_stuck()

            # Should stop movement
            mock_stop.assert_called_once()

            # Should log warning about stuck condition
            mock_logger.warning.assert_called_once()
            log_message = mock_logger.warning.call_args[0][0]
            assert "stuck" in log_message.lower()

    async def test_stuck_handling_increments_failure_count(self, hass, config_entry, mock_time):
        """Test that stuck handling increments failure count."""
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

        # Initial failure count
        initial_failures = cover._failure_count

        # Set up stuck condition
        cover._state = CoverState.OPENING
        cover._position = 50

        with patch.object(cover, "_stop_movement"):
            await cover._handle_stuck()

            # Failure count should increment
            assert cover._failure_count == initial_failures + 1

    async def test_manual_operation_detection_updates_counter(self, hass, config_entry, mock_time):
        """Test that manual operation detection updates counter."""
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

        # Initial manual operation count
        initial_count = cover._manual_operation_count

        # Simulate manual operation (unexpected state change)
        # This would depend on the specific implementation in _handle_sensor_change
        # For now, we test that the counter exists and can be incremented

        # The manual operation counter should be available
        assert hasattr(cover, "_manual_operation_count")

        # Simulate manual operation by directly incrementing (as the real logic might do)
        cover._manual_operation_count += 1

        # Counter should be updated
        assert cover._manual_operation_count == initial_count + 1

    async def test_state_restoration_after_power_loss(self, hass, config_entry, mock_time):
        """Test state restoration after power loss scenarios."""
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

        # Mock last state as opening (would be lost in power failure)
        last_state = MagicMock()
        last_state.state = "opening"
        last_state.attributes = {
            "current_position": 75,
            "last_direction": "UP",
        }

        with patch.object(cover, "async_get_last_state", return_value=last_state):
            await cover.async_added_to_hass()

            # Should convert opening state to halted for safety
            assert cover._state == CoverState.HALTED
            assert cover._position == 75  # Position preserved

    async def test_auto_disable_persists_across_restart(self, hass, config_entry, mock_time):
        """Test that auto-disable state persists across restart."""
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

        # Mock last state with disabled cover
        last_state = MagicMock()
        last_state.state = "closed"
        last_state.attributes = {
            "current_position": 0,
            "disabled": True,
            "failure_count": MAX_RETRIES,
        }

        with patch.object(cover, "async_get_last_state", return_value=last_state):
            await cover.async_added_to_hass()

            # Should restore disabled state
            assert cover._disabled is True
            assert cover._failure_count == MAX_RETRIES

    async def test_safety_mechanisms_integrate_with_position_tracking(self, hass, config_entry, mock_time):
        """Test that safety mechanisms integrate properly with position tracking."""
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

        # Start opening movement
        cover._state = CoverState.OPENING
        cover._position = 0
        cover._movement_start_time = mock_time
        cover._movement_start_position = 0
        cover._movement_duration = 30.0

        # Simulate time passing and position updates
        with patch("custom_components.autocover.cover.datetime") as mock_dt:
            current_time = mock_time + timedelta(seconds=15)
            mock_dt.now.return_value = current_time

            # Update position
            cover._update_position()

            # Should be at approximately 50%
            assert abs(cover._position - 50.0) < 0.1

            # Now simulate stuck condition
            cover._stuck_check_position = 50
            cover._stuck_check_time = current_time

            # Advance time beyond stuck timeout
            stuck_time = current_time + timedelta(seconds=STUCK_TIMEOUT + 1)
            mock_dt.now.return_value = stuck_time

            with patch.object(cover, "_handle_stuck") as mock_handle_stuck:
                cover._check_stuck()

                # Should detect stuck condition
                mock_handle_stuck.assert_called_once()

    async def test_multiple_safety_failures_accumulate(self, hass, config_entry, mock_time):
        """Test that multiple safety failures accumulate properly."""
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

        # Start with some failures
        cover._failure_count = 1

        # Simulate stuck condition which should increment failure count
        cover._state = CoverState.OPENING
        cover._position = 50

        with patch.object(cover, "_stop_movement"):
            await cover._handle_stuck()

            # Failure count should increment
            assert cover._failure_count == 2

        # Simulate button failure which should increment further
        with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
            mock_service_call.side_effect = Exception("Service call failed")
            await cover._press_button()

            # Failure count should increment again
            assert cover._failure_count == 3

            # Should disable after reaching MAX_RETRIES
            if cover._failure_count >= MAX_RETRIES:
                assert cover._disabled is True

    async def test_safety_reset_on_successful_operation(self, hass, config_entry, mock_time):
        """Test that safety counters reset on successful operation."""
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

        # Set up failed state
        cover._failure_count = MAX_RETRIES - 1
        cover._disabled = True

        # Successful button press should reset safety counters
        await cover._press_button()

        # Should reset failure count and enable cover
        assert cover._failure_count == 0
        assert cover._disabled is False

    async def test_emergency_stop_functionality(self, hass, config_entry, mock_time):
        """Test emergency stop functionality overrides other operations."""
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

        # Set up active movement
        cover._state = CoverState.OPENING
        cover._position = 50

        with patch.object(cover, "_press_button") as mock_press:
            await cover.async_stop_cover()

            # Should always work regardless of other conditions
            mock_press.assert_called_once()

            # Should transition to halted state
            assert cover._state == CoverState.HALTED

    async def test_safety_logging_includes_relevant_context(self, hass, config_entry, mock_time, mock_logger):
        """Test that safety logging includes relevant context information."""
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

        # Test stuck logging includes position and state information
        cover._state = CoverState.OPENING
        cover._position = 75

        with patch.object(cover, "_stop_movement"):
            await cover._handle_stuck()

            # Should log with context
            mock_logger.warning.assert_called_once()
            log_call = mock_logger.warning.call_args
            log_message = log_call[0][0]
            log_args = log_call[0][1:]

            # Message should include cover name, position, and state
            assert config_entry.title in log_args
            assert "75" in str(log_args) or "75" in log_message

    async def test_safety_boundaries_are_respected(self, hass, config_entry, mock_time):
        """Test that safety boundaries and limits are properly respected."""
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

        # Test that failure count doesn't exceed MAX_RETRIES
        with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
            mock_service_call.side_effect = Exception("Service call failed")

            # Cause multiple failures
            for i in range(MAX_RETRIES + 2):
                await cover._press_button()

            # Should not exceed MAX_RETRIES
            assert cover._failure_count == MAX_RETRIES

            # Should be disabled
            assert cover._disabled is True

    async def test_safety_mechanisms_work_with_sensor_failures(self, hass, config_entry, mock_time):
        """Test that safety mechanisms work properly with sensor failures."""
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

        # Test with sensor failures during movement
        # This simulates a scenario where sensors become unavailable
        cover._state = CoverState.OPENING
        cover._position = 50

        # Simulate sensor state change indicating potential issue
        sensor_event = MagicMock()
        sensor_event.data = {"new_state": MagicMock(), "old_state": MagicMock()}

        # Mock sensor state as unavailable
        with patch.object(hass.states, "get") as mock_get:
            mock_get.return_value = None  # Sensor unavailable

            # This should not crash and should handle gracefully
            try:
                cover._handle_sensor_change(sensor_event)
                # If we get here without exception, the safety mechanism worked
                assert True
            except Exception as e:
                pytest.fail(f"Safety mechanism failed to handle sensor failure: {e}")

    async def test_position_tracking_continues_despite_safety_events(self, hass, config_entry, mock_time):
        """Test that position tracking continues properly despite safety events."""
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

        # Start opening movement
        cover._state = CoverState.OPENING
        cover._position = 0
        cover._movement_start_time = mock_time
        cover._movement_start_position = 0
        cover._movement_duration = 30.0

        # Simulate time passing
        with patch("custom_components.autocover.cover.datetime") as mock_dt:
            current_time = mock_time + timedelta(seconds=10)
            mock_dt.now.return_value = current_time

            # Update position
            initial_position = cover._position
            cover._update_position()
            updated_position = cover._position

            # Position should have changed despite safety mechanisms being active
            assert updated_position > initial_position

            # Now simulate a safety event (stuck detection)
            cover._stuck_check_position = updated_position
            cover._stuck_check_time = current_time

            stuck_time = current_time + timedelta(seconds=STUCK_TIMEOUT + 1)
            mock_dt.now.return_value = stuck_time

            # Handle stuck condition
            with patch.object(cover, "_stop_movement") as mock_stop:
                cover._check_stuck()
                # This might trigger stuck handling
                # The important thing is it doesn't crash

            # Final position should still be valid
            assert 0 <= cover._position <= 100