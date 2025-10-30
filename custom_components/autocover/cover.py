"""Cover platform for Auto Cover integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
)
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    BUTTON_ACTIVATION_TIME,
    CONF_BUTTON_ENTITY,
    CONF_CLOSED_SENSOR,
    CONF_OPEN_SENSOR,
    CONF_THRESHOLD,
    CONF_TIME_TO_CLOSE,
    CONF_TIME_TO_OPEN,
    CoverState,
    DOMAIN,
    MAX_RETRIES,
    POSITION_UPDATE_INTERVAL,
    STUCK_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

# Debounce time for rapid commands
DEBOUNCE_TIME = 0.6  # seconds


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Auto Cover from a config entry."""
    config = config_entry.data
    
    cover = AutoCover(
        hass=hass,
        name=config_entry.title,
        unique_id=config_entry.entry_id,
        button_entity=config[CONF_BUTTON_ENTITY],
        time_to_open=config[CONF_TIME_TO_OPEN],
        time_to_close=config[CONF_TIME_TO_CLOSE],
        closed_sensor=config.get(CONF_CLOSED_SENSOR),
        open_sensor=config.get(CONF_OPEN_SENSOR),
        threshold=config.get(CONF_THRESHOLD, 10),
    )
    
    async_add_entities([cover])


class AutoCover(CoverEntity, RestoreEntity):
    """Representation of an Auto Cover."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        unique_id: str,
        button_entity: str,
        time_to_open: float,
        time_to_close: float,
        closed_sensor: str | None,
        open_sensor: str | None,
        threshold: int,
    ) -> None:
        """Initialize the cover."""
        self.hass = hass
        self._attr_name = name
        self._attr_unique_id = unique_id
        
        # Configuration
        self._button_entity = button_entity
        self._time_to_open = time_to_open
        self._time_to_close = time_to_close
        self._closed_sensor = closed_sensor
        self._open_sensor = open_sensor
        self._threshold = threshold
        
        # State variables
        self._state = CoverState.CLOSED
        self._position = 0  # 0-100%
        self._next_direction = "UP"  # Direction of next button press: "UP" or "DOWN"
        self._target_position = None
        
        # Movement tracking
        self._movement_start_time = None
        self._movement_start_position = None
        self._movement_duration = None
        
        # Button tracking
        self._button_pressing = False
        self._button_press_time = None
        self._last_command_time = None
        
        # Safety tracking
        self._failure_count = 0
        self._disabled = False
        self._stuck_check_position = None
        self._stuck_check_time = None
        
        # Obstacle detection
        self._obstacle_check_handle = None
        self._obstacle_detected_count = 0
        
        # Scheduled stop handle
        self._scheduled_stop_handle = None
        
        # Manual operation tracking
        self._manual_operation_count = 0
        
        # Listeners
        self._position_update_handle = None
        self._sensor_listeners = []
        
        # Supported features
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information about this cover."""
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": self._attr_name,
            "manufacturer": "Auto Cover",
            "model": "Virtual Cover",
            "sw_version": "1.0",
        }

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover (0-100)."""
        return int(self._position)

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        return self._state == CoverState.OPENING

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        return self._state == CoverState.CLOSING

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed."""
        return self._position == 0 or self._state == CoverState.CLOSED

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        operation_mode = "no_sensors"
        if self._closed_sensor and self._open_sensor:
            operation_mode = "full_sensors"
        elif self._closed_sensor or self._open_sensor:
            operation_mode = "single_sensor"
        
        return {
            "current_position": self._position,
            "next_direction": self._next_direction,
            "operation_mode": operation_mode,
            "button_entity": self._button_entity,
            "button_last_press": self._button_press_time.isoformat() if self._button_press_time else None,
            "obstacle_detected_count": self._obstacle_detected_count,
            "manual_operation_count": self._manual_operation_count,
            "sensor_open_entity": self._open_sensor,
            "sensor_closed_entity": self._closed_sensor,
            "time_to_open": self._time_to_open,
            "time_to_close": self._time_to_close,
            "threshold_percentage": self._threshold,
            "disabled": self._disabled,
            "failure_count": self._failure_count,
        }

    async def async_added_to_hass(self) -> None:
        """Register callbacks and restore state."""
        await super().async_added_to_hass()
        
        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state:
            self._position = last_state.attributes.get("current_position", 0)
            # Restore next_direction, defaulting based on position
            self._next_direction = last_state.attributes.get("next_direction")
            if self._next_direction is None:
                # If no saved direction, infer from position
                self._next_direction = "UP" if self._position < 50 else "DOWN"
            self._obstacle_detected_count = last_state.attributes.get("obstacle_detected_count", 0)
            self._manual_operation_count = last_state.attributes.get("manual_operation_count", 0)
            
            # Don't restore OPENING/CLOSING states - default to HALTED
            if last_state.state in [STATE_OPENING, STATE_CLOSING]:
                self._state = CoverState.HALTED
                _LOGGER.info(
                    "Restored cover %s from %s state to HALTED at position %d%%",
                    self._attr_name,
                    last_state.state,
                    self._position,
                )
            else:
                # Map HA states to our CoverState enum
                state_map = {
                    STATE_CLOSED: CoverState.CLOSED,
                    STATE_OPEN: CoverState.OPEN,
                    "halted": CoverState.HALTED,
                }
                self._state = state_map.get(last_state.state, CoverState.HALTED)
        
        # Initialize position based on sensors
        await self._sync_position_from_sensors()
        
        # Register sensor state change listeners
        if self._closed_sensor:
            self._sensor_listeners.append(
                async_track_state_change_event(
                    self.hass,
                    self._closed_sensor,
                    self._handle_sensor_change,
                )
            )
        
        if self._open_sensor:
            self._sensor_listeners.append(
                async_track_state_change_event(
                    self.hass,
                    self._open_sensor,
                    self._handle_sensor_change,
                )
            )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up when entity is removed."""
        # Cancel position update timer
        if self._position_update_handle:
            self._position_update_handle()
            self._position_update_handle = None

        # Cancel obstacle check
        if self._obstacle_check_handle:
            self._obstacle_check_handle.cancel()
            self._obstacle_check_handle = None
        
        # Cancel scheduled stop
        if self._scheduled_stop_handle:
            self._scheduled_stop_handle.cancel()
            self._scheduled_stop_handle = None
        
        # Remove sensor listeners
        for remove_listener in self._sensor_listeners:
            remove_listener()
        self._sensor_listeners.clear()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        if self._disabled:
            _LOGGER.error("Cover %s is disabled due to failures", self._attr_name)
            return
        
        # Debounce rapid commands
        if not self._should_process_command():
            _LOGGER.warning("Ignoring rapid open command for %s", self._attr_name)
            return
        
        _LOGGER.info("Opening cover %s", self._attr_name)
        
        # Determine action based on current state
        if self._state == CoverState.CLOSING:
            # Stop first, then open
            await self._stop_movement()
            await asyncio.sleep(BUTTON_ACTIVATION_TIME + 0.1)  # Wait for button to be available
        
        if self._state in [CoverState.CLOSED, CoverState.HALTED]:
            await self._start_opening()
        elif self._state == CoverState.OPEN:
            _LOGGER.debug("Cover %s is already open", self._attr_name)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        if self._disabled:
            _LOGGER.error("Cover %s is disabled due to failures", self._attr_name)
            return
        
        # Debounce rapid commands
        if not self._should_process_command():
            _LOGGER.warning("Ignoring rapid close command for %s", self._attr_name)
            return
        
        _LOGGER.info("Closing cover %s", self._attr_name)
        
        # Determine action based on current state
        if self._state == CoverState.OPENING:
            # Stop first, then close
            await self._stop_movement()
            await asyncio.sleep(BUTTON_ACTIVATION_TIME + 0.1)  # Wait for button to be available
        
        if self._state in [CoverState.OPEN, CoverState.HALTED]:
            await self._start_closing()
        elif self._state == CoverState.CLOSED:
            _LOGGER.debug("Cover %s is already closed", self._attr_name)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        if self._disabled:
            _LOGGER.error("Cover %s is disabled due to failures", self._attr_name)
            return
        
        # Only stop if cover is actively moving to prevent unintended movement
        # Pressing the button when stationary (OPEN/CLOSED/HALTED) would start movement
        if self._state not in [CoverState.OPENING, CoverState.CLOSING]:
            _LOGGER.debug(
                "Stop command ignored for %s - cover is not moving (state: %s)",
                self._attr_name,
                self._state
            )
            return
        
        _LOGGER.info("Stopping cover %s", self._attr_name)
        await self._stop_movement()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        if self._disabled:
            _LOGGER.error("Cover %s is disabled due to failures", self._attr_name)
            return
        
        position = kwargs[ATTR_POSITION]
        
        # Debounce rapid commands
        if not self._should_process_command():
            _LOGGER.warning("Ignoring rapid set position command for %s", self._attr_name)
            return
        
        _LOGGER.info("Setting cover %s to position %d%%", self._attr_name, position)
        
        # If already at target position, do nothing
        if abs(self._position - position) < 2:  # 2% tolerance
            _LOGGER.debug("Cover %s already at position %d%%", self._attr_name, position)
            return
        
        # Stop current movement if any
        if self._state in [CoverState.OPENING, CoverState.CLOSING]:
            await self._stop_movement()
            await asyncio.sleep(BUTTON_ACTIVATION_TIME + 0.1)  # Wait for button to be available
        
        # Determine direction
        if position > self._position:
            await self._start_opening(target_position=position)
        else:
            await self._start_closing(target_position=position)

    async def _start_opening(self, target_position: int = 100) -> None:
        """Start opening the cover."""
        # Cancel any previously scheduled stop
        if self._scheduled_stop_handle:
            self._scheduled_stop_handle.cancel()
            self._scheduled_stop_handle = None
        
        self._target_position = target_position
        self._movement_start_position = self._position
        self._movement_start_time = datetime.now()
        
        # Calculate movement duration
        position_delta = self._target_position - self._movement_start_position
        self._movement_duration = (position_delta / 100) * self._time_to_open
        
        # Transition to OPENING state
        self._state = CoverState.OPENING
        self.async_write_ha_state()
        
        # Check if button is in wrong direction
        if self._next_direction == "DOWN":
            # Button would close, need to press twice to correct direction
            _LOGGER.debug(
                "Cover %s: correcting direction from DOWN to UP (double press)",
                self._attr_name
            )
            await self._press_button()  # First press to toggle direction
            await asyncio.sleep(BUTTON_ACTIVATION_TIME + 0.1)
            await self._press_button()  # Second press to start opening
        else:
            # Button is already set to open, press once
            await self._press_button()
        
        # After starting to open, next button press will close (or stop then close)
        self._next_direction = "DOWN"
        
        # Start position tracking
        self._start_position_tracking()
        
        # Schedule obstacle check
        self._schedule_obstacle_check()
        
        # For partial positions, schedule stop
        if target_position < 100:
            self._schedule_stop_at_position()

    async def _start_closing(self, target_position: int = 0) -> None:
        """Start closing the cover."""
        # Cancel any previously scheduled stop
        if self._scheduled_stop_handle:
            self._scheduled_stop_handle.cancel()
            self._scheduled_stop_handle = None
        
        self._target_position = target_position
        self._movement_start_position = self._position
        self._movement_start_time = datetime.now()
        
        # Calculate movement duration
        position_delta = self._movement_start_position - self._target_position
        self._movement_duration = (position_delta / 100) * self._time_to_close
        
        # Transition to CLOSING state
        self._state = CoverState.CLOSING
        self.async_write_ha_state()
        
        # Check if button is in wrong direction
        if self._next_direction == "UP":
            # Button would open, need to press twice to correct direction
            _LOGGER.debug(
                "Cover %s: correcting direction from UP to DOWN (double press)",
                self._attr_name
            )
            await self._press_button()  # First press to toggle direction
            await asyncio.sleep(BUTTON_ACTIVATION_TIME + 0.1)
            await self._press_button()  # Second press to start closing
        else:
            # Button is already set to close, press once
            await self._press_button()
        
        # After starting to close, next button press will open (or stop then open)
        self._next_direction = "UP"
        
        # Start position tracking
        self._start_position_tracking()
        
        # Schedule obstacle check
        self._schedule_obstacle_check()
        
        # For partial positions, schedule stop
        if target_position > 0:
            self._schedule_stop_at_position()

    async def _stop_movement(self) -> None:
        """Stop cover movement."""
        # Press button to stop
        await self._press_button()
        
        # Update position one last time
        self._update_position()
        
        # Transition to HALTED state
        # Note: next_direction was already set correctly when movement started
        # (OPENING sets next to DOWN, CLOSING sets next to UP)
        self._state = CoverState.HALTED
        
        # Stop position tracking
        self._stop_position_tracking()
        
        # Cancel obstacle check
        if self._obstacle_check_handle:
            self._obstacle_check_handle.cancel()
            self._obstacle_check_handle = None
        
        # Cancel scheduled stop
        if self._scheduled_stop_handle:
            self._scheduled_stop_handle.cancel()
            self._scheduled_stop_handle = None
        
        # Reset movement variables
        self._movement_start_time = None
        self._movement_start_position = None
        self._movement_duration = None
        self._target_position = None
        
        self.async_write_ha_state()
        _LOGGER.info("Cover %s stopped at position %d%%", self._attr_name, self._position)

    async def _press_button(self) -> None:
        """Press the button entity."""
        # Check if button is currently being pressed
        if self._button_pressing:
            current_time = datetime.now()
            elapsed = (current_time - self._button_press_time).total_seconds()
            if elapsed < BUTTON_ACTIVATION_TIME:
                wait_time = BUTTON_ACTIVATION_TIME - elapsed + 0.05  # Add small buffer
                _LOGGER.debug(
                    "Button %s is active, waiting %.2fs",
                    self._button_entity,
                    wait_time,
                )
                await asyncio.sleep(wait_time)
        
        try:
            _LOGGER.debug("Pressing button %s", self._button_entity)
            await self.hass.services.async_call(
                "button",
                "press",
                {"entity_id": self._button_entity},
                blocking=True,
            )
            
            # Track button press
            self._button_pressing = True
            self._button_press_time = datetime.now()
            self._failure_count = 0  # Reset failure count on success
            
            # Schedule button release tracking
            async def release_button():
                self._button_pressing = False
                _LOGGER.debug("Button %s released", self._button_entity)
            
            self.hass.loop.call_later(BUTTON_ACTIVATION_TIME, lambda: asyncio.create_task(release_button()))
            
        except Exception as err:
            _LOGGER.error("Failed to press button %s: %s", self._button_entity, err)
            self._failure_count += 1
            
            if self._failure_count >= MAX_RETRIES:
                _LOGGER.error(
                    "Cover %s disabled after %d consecutive failures",
                    self._attr_name,
                    MAX_RETRIES,
                )
                self._disabled = True
                self.async_write_ha_state()

    def _should_process_command(self) -> bool:
        """Check if command should be processed (debouncing)."""
        current_time = datetime.now()
        
        if self._last_command_time is None:
            self._last_command_time = current_time
            return True
        
        elapsed = (current_time - self._last_command_time).total_seconds()
        self._last_command_time = current_time
        
        if elapsed < DEBOUNCE_TIME:
            _LOGGER.debug(
                "Command debounced for %s (%.2fs since last command)",
                self._attr_name,
                elapsed,
            )
            return False
        
        return True

    def _start_position_tracking(self) -> None:
        """Start tracking position updates."""
        if self._position_update_handle:
            self._position_update_handle()
        
        # Initialize stuck detection
        self._stuck_check_position = self._position
        self._stuck_check_time = datetime.now()
        
        # Schedule periodic position updates
        self._position_update_handle = async_track_time_interval(
            self.hass,
            self._position_update_callback,
            timedelta(seconds=POSITION_UPDATE_INTERVAL),
        )
        
        _LOGGER.debug("Started position tracking for %s", self._attr_name)

    def _stop_position_tracking(self) -> None:
        """Stop tracking position updates."""
        if self._position_update_handle:
            self._position_update_handle()
            self._position_update_handle = None
        
        _LOGGER.debug("Stopped position tracking for %s", self._attr_name)

    @callback
    def _position_update_callback(self, now: datetime) -> None:
        """Update position based on elapsed time."""
        self._update_position()
        
        # Check for stuck condition
        self._check_stuck()
        
        # Check if target position reached
        if self._target_position is not None:
            tolerance = 2  # 2% tolerance
            if abs(self._position - self._target_position) < tolerance:
                _LOGGER.info(
                    "Cover %s reached target position %d%%",
                    self._attr_name,
                    self._target_position,
                )
                self.hass.create_task(self._handle_position_reached())

    def _update_position(self) -> None:
        """Calculate and update current position based on elapsed time."""
        if self._movement_start_time is None:
            return
        
        elapsed = (datetime.now() - self._movement_start_time).total_seconds()
        
        if self._state == CoverState.OPENING:
            # Calculate progress
            if self._movement_duration > 0:
                progress = min(elapsed / self._movement_duration, 1.0)
                position_delta = self._target_position - self._movement_start_position
                self._position = self._movement_start_position + (progress * position_delta)
            
            # Clamp to target
            self._position = min(self._position, self._target_position)
            
        elif self._state == CoverState.CLOSING:
            # Calculate progress
            if self._movement_duration > 0:
                progress = min(elapsed / self._movement_duration, 1.0)
                position_delta = self._movement_start_position - self._target_position
                self._position = self._movement_start_position - (progress * position_delta)
            
            # Clamp to target
            self._position = max(self._position, self._target_position)
        
        # Clamp to valid range
        self._position = max(0, min(100, self._position))
        
        self.async_write_ha_state()
        
        _LOGGER.debug(
            "Cover %s position updated to %d%% (target: %d%%)",
            self._attr_name,
            self._position,
            self._target_position,
        )

    def _check_stuck(self) -> None:
        """Check if cover is stuck (not moving)."""
        if self._stuck_check_time is None:
            return
        
        elapsed = (datetime.now() - self._stuck_check_time).total_seconds()
        position_change = abs(self._position - self._stuck_check_position)
        
        if elapsed >= STUCK_TIMEOUT and position_change < 1:  # Less than 1% change
            _LOGGER.error(
                "Cover %s appears stuck at position %d%% (no movement for %ds)",
                self._attr_name,
                self._position,
                STUCK_TIMEOUT,
            )
            self.hass.create_task(self._handle_stuck())
        else:
            # Update stuck check position periodically
            if elapsed >= 1.0:  # Check every second
                self._stuck_check_position = self._position
                self._stuck_check_time = datetime.now()

    async def _handle_stuck(self) -> None:
        """Handle stuck condition."""
        await self._stop_movement()
        self._failure_count += 1
        
        if self._failure_count >= MAX_RETRIES:
            _LOGGER.error(
                "Cover %s disabled after stuck detection (%d failures)",
                self._attr_name,
                MAX_RETRIES,
            )
            self._disabled = True

    async def _handle_position_reached(self) -> None:
        """Handle reaching target position."""
        # For full open/close, wait for sensor confirmation if available
        if self._target_position == 100 or self._target_position == 0:
            # Let obstacle detection handle it
            return
        
        # For partial positions, just stop
        await self._stop_movement()

    def _schedule_obstacle_check(self) -> None:
        """Schedule obstacle detection check after threshold time."""
        if self._obstacle_check_handle:
            self._obstacle_check_handle.cancel()
            self._obstacle_check_handle = None
        
        # Calculate check time with threshold
        threshold_time = self._movement_duration * (1 + self._threshold / 100)
        
        _LOGGER.debug(
            "Scheduling obstacle check for %s in %.2fs (expected: %.2fs, threshold: %d%%)",
            self._attr_name,
            threshold_time,
            self._movement_duration,
            self._threshold,
        )
        
        self._obstacle_check_handle = self.hass.loop.call_later(
            threshold_time,
            lambda: self.hass.create_task(self._check_obstacle()),
        )

    def _schedule_stop_at_position(self) -> None:
        """Schedule stop button press when target position should be reached."""
        if self._movement_duration <= 0:
            return
        
        async def stop_at_position():
            if self._state in [CoverState.OPENING, CoverState.CLOSING]:
                _LOGGER.info(
                    "Stopping cover %s at target position %d%%",
                    self._attr_name,
                    self._target_position,
                )
                await self._stop_movement()
        
        self._scheduled_stop_handle = self.hass.loop.call_later(
            self._movement_duration,
            lambda: self.hass.create_task(stop_at_position()),
        )

    async def _check_obstacle(self) -> None:
        """Check for obstacles after threshold time."""
        _LOGGER.debug("Checking for obstacles on %s", self._attr_name)
        
        obstacle_detected = False
        
        if self._target_position == 100 and self._open_sensor:
            # Should be fully open
            # For door/opening sensors: "on" typically means open
            sensor_state = self.hass.states.get(self._open_sensor)
            if sensor_state and sensor_state.state == "on":
                # Sensor confirms open - success, no obstacle
                pass
            elif sensor_state and sensor_state.state in ["off", "unavailable", "unknown"]:
                # Sensor doesn't confirm open - obstacle detected
                obstacle_detected = True
                _LOGGER.warning(
                    "Obstacle detected on %s: open sensor shows %s (expected on)",
                    self._attr_name,
                    sensor_state.state,
                )
        
        elif self._target_position == 0 and self._closed_sensor:
            # Should be fully closed
            # For door/opening sensors: "off" typically means closed
            sensor_state = self.hass.states.get(self._closed_sensor)
            if sensor_state and sensor_state.state == "off":
                # Sensor confirms closed - success, no obstacle
                pass
            elif sensor_state and sensor_state.state in ["on", "unavailable", "unknown"]:
                # Sensor doesn't confirm closed - obstacle detected
                obstacle_detected = True
                _LOGGER.warning(
                    "Obstacle detected on %s: closed sensor shows %s (expected off)",
                    self._attr_name,
                    sensor_state.state,
                )
        
        if obstacle_detected:
            await self._handle_obstacle()
        else:
            # Position reached successfully
            if self._target_position == 100:
                self._position = 100
                self._state = CoverState.OPEN
                # When fully open, next button press will close
                self._next_direction = "DOWN"
            elif self._target_position == 0:
                self._position = 0
                self._state = CoverState.CLOSED
                # When fully closed, next button press will open
                self._next_direction = "UP"
            
            self._stop_position_tracking()
            self.async_write_ha_state()
            _LOGGER.info(
                "Cover %s reached position %d%% successfully",
                self._attr_name,
                self._target_position,
            )

    async def _handle_obstacle(self) -> None:
        """Handle obstacle detection."""
        self._obstacle_detected_count += 1
        
        # Determine where the physical cover will end up after auto-reverse
        # If closing (going down), it reverses to fully open
        # If opening (going up), it reverses to fully closed
        if self._state == CoverState.CLOSING:
            final_position = 100
            final_state = CoverState.OPEN
            # After reaching fully open, next press will close
            self._next_direction = "DOWN"
        else:  # OPENING
            final_position = 0
            final_state = CoverState.CLOSED
            # After reaching fully closed, next press will open
            self._next_direction = "UP"
        
        _LOGGER.warning(
            "Obstacle detected on cover %s at position %d%% (count: %d) - physical cover reversing to %s",
            self._attr_name,
            self._position,
            self._obstacle_detected_count,
            "fully open" if final_position == 100 else "fully closed",
        )
        
        # Update to final position and state
        self._position = final_position
        self._state = final_state
        
        # Stop position tracking
        self._stop_position_tracking()
        
        # Cancel obstacle check
        if self._obstacle_check_handle:
            self._obstacle_check_handle.cancel()
            self._obstacle_check_handle = None
        
        # Cancel scheduled stop
        if self._scheduled_stop_handle:
            self._scheduled_stop_handle.cancel()
            self._scheduled_stop_handle = None
        
        # Reset movement variables
        self._movement_start_time = None
        self._movement_start_position = None
        self._movement_duration = None
        self._target_position = None
        
        self.async_write_ha_state()
        
        # Don't press button - let the physical cover handle the reversal

    @callback
    def _handle_sensor_change(self, event) -> None:
        """Handle sensor state changes."""
        entity_id = event.data.get("entity_id")
        old_state: State | None = event.data.get("old_state")
        new_state: State | None = event.data.get("new_state")
        
        if new_state is None or new_state.state == "unavailable":
            return
        
        _LOGGER.debug(
            "Sensor %s changed from %s to %s",
            entity_id,
            old_state.state if old_state else "unknown",
            new_state.state,
        )
        
        # Check for manual operation (sensor change while idle)
        if self._state not in [CoverState.OPENING, CoverState.CLOSING]:
            # For door/opening sensors: "off" = closed, "on" = open
            if entity_id == self._closed_sensor and new_state.state == "off":
                if self._position != 0:
                    _LOGGER.info("Manual operation detected on %s: closed", self._attr_name)
                    self._position = 0
                    self._state = CoverState.CLOSED
                    # When fully closed, next button press will open
                    self._next_direction = "UP"
                    self._manual_operation_count += 1
                    self.async_write_ha_state()
            
            elif entity_id == self._open_sensor and new_state.state == "on":
                if self._position != 100:
                    _LOGGER.info("Manual operation detected on %s: opened", self._attr_name)
                    self._position = 100
                    self._state = CoverState.OPEN
                    # When fully open, next button press will close
                    self._next_direction = "DOWN"
                    self._manual_operation_count += 1
                    self.async_write_ha_state()

    async def _sync_position_from_sensors(self) -> None:
        """Synchronize position from sensor states."""
        # For door/opening sensors: "off" = closed, "on" = open
        if self._closed_sensor:
            sensor_state = self.hass.states.get(self._closed_sensor)
            if sensor_state and sensor_state.state == "off":
                self._position = 0
                self._state = CoverState.CLOSED
                # When fully closed, next button press will open
                self._next_direction = "UP"
                _LOGGER.debug("Initialized %s as closed from sensor", self._attr_name)
                return
        
        if self._open_sensor:
            sensor_state = self.hass.states.get(self._open_sensor)
            if sensor_state and sensor_state.state == "on":
                self._position = 100
                self._state = CoverState.OPEN
                # When fully open, next button press will close
                self._next_direction = "DOWN"
                _LOGGER.debug("Initialized %s as open from sensor", self._attr_name)
                return
        
        # If no sensor confirms position, keep restored position
        _LOGGER.debug(
            "No sensor confirmation for %s, keeping position %d%%",
            self._attr_name,
            self._position,
        )