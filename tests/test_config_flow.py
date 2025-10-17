"""Tests for Auto Cover config flow."""
from __future__ import annotations

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.autocover.config_flow import AutoCoverConfigFlow, _get_schema, _validate_input
from custom_components.autocover.const import (
    CONF_BUTTON_ENTITY,
    CONF_CLOSED_SENSOR,
    CONF_OPEN_SENSOR,
    CONF_THRESHOLD,
    CONF_TIME_TO_CLOSE,
    CONF_TIME_TO_OPEN,
    DEFAULT_THRESHOLD,
    DOMAIN,
)


class TestAutoCoverConfigFlow:
    """Test cases for the Auto Cover config flow."""

    def test_get_schema_creates_proper_voluptuous_schema(self):
        """Test that _get_schema creates a proper voluptuous schema."""
        schema = _get_schema()

        # Check that schema has the expected fields
        assert CONF_BUTTON_ENTITY in schema.schema
        assert CONF_TIME_TO_OPEN in schema.schema
        assert CONF_TIME_TO_CLOSE in schema.schema
        assert CONF_OPEN_SENSOR in schema.schema
        assert CONF_CLOSED_SENSOR in schema.schema
        assert CONF_THRESHOLD in schema.schema

    def test_get_schema_with_user_input_prepopulates_defaults(self):
        """Test that _get_schema prepopulates defaults from user input."""
        user_input = {
            CONF_BUTTON_ENTITY: "button.test",
            CONF_TIME_TO_OPEN: 45.0,
            CONF_TIME_TO_CLOSE: 35.0,
        }

        schema = _get_schema(user_input)

        # Check that the schema contains the user input as defaults
        assert schema.schema[CONF_BUTTON_ENTITY].default == "button.test"
        assert schema.schema[CONF_TIME_TO_OPEN].default == 45.0
        assert schema.schema[CONF_TIME_TO_CLOSE].default == 35.0

    def test_validate_input_with_valid_data_returns_no_errors(self, hass, mock_states, mock_entity_registry):
        """Test that _validate_input returns no errors for valid input."""
        hass.helpers.entity_registry.async_get = mock_entity_registry
        config_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
            CONF_OPEN_SENSOR: "binary_sensor.open_sensor",
            CONF_CLOSED_SENSOR: "binary_sensor.closed_sensor",
            CONF_THRESHOLD: DEFAULT_THRESHOLD,
        }

        errors = _validate_input(hass, config_data)

        assert errors == {}

    def test_validate_input_with_missing_button_entity_returns_error(self, hass, mock_states):
        """Test that _validate_input returns error for missing button entity."""
        config_data = {
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
        }

        errors = _validate_input(hass, config_data)

        assert CONF_BUTTON_ENTITY in errors
        assert errors[CONF_BUTTON_ENTITY] == "invalid_entity"

    def test_validate_input_with_invalid_button_entity_format_returns_error(self, hass, mock_states):
        """Test that _validate_input returns error for invalid button entity format."""
        config_data = {
            CONF_BUTTON_ENTITY: "invalid_button_format",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
        }

        errors = _validate_input(hass, config_data)

        assert CONF_BUTTON_ENTITY in errors
        assert errors[CONF_BUTTON_ENTITY] == "invalid_entity"

    def test_validate_input_with_nonexistent_button_entity_returns_error(self, hass, mock_entity_registry):
        """Test that _validate_input returns error for non-existent button entity."""
        hass.helpers.entity_registry.async_get = mock_entity_registry
        mock_entity_registry.async_get.return_value = None
        hass.states.async_entity_ids.return_value = []

        config_data = {
            CONF_BUTTON_ENTITY: "button.nonexistent",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
        }

        errors = _validate_input(hass, config_data)

        assert CONF_BUTTON_ENTITY in errors
        assert errors[CONF_BUTTON_ENTITY] == "invalid_entity"

    def test_validate_input_with_invalid_sensor_format_returns_error(self, hass, mock_states):
        """Test that _validate_input returns error for invalid sensor format."""
        config_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_OPEN_SENSOR: "invalid_sensor_format",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
        }

        errors = _validate_input(hass, config_data)

        assert CONF_OPEN_SENSOR in errors
        assert errors[CONF_OPEN_SENSOR] == "invalid_entity"

    def test_validate_input_with_nonexistent_sensor_returns_error(self, hass, mock_entity_registry):
        """Test that _validate_input returns error for non-existent sensor."""
        hass.helpers.entity_registry.async_get = mock_entity_registry
        mock_entity_registry.async_get.return_value = None
        hass.states.async_entity_ids.return_value = []

        config_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_OPEN_SENSOR: "binary_sensor.nonexistent",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
        }

        errors = _validate_input(hass, config_data)

        assert CONF_OPEN_SENSOR in errors
        assert errors[CONF_OPEN_SENSOR] == "invalid_entity"

    def test_validate_input_with_invalid_time_to_open_returns_error(self, hass, mock_states):
        """Test that _validate_input returns error for invalid time to open."""
        config_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: -5.0,  # Invalid negative time
            CONF_TIME_TO_CLOSE: 25.0,
        }

        errors = _validate_input(hass, config_data)

        assert CONF_TIME_TO_OPEN in errors
        assert errors[CONF_TIME_TO_OPEN] == "invalid_time"

    def test_validate_input_with_zero_time_to_open_returns_error(self, hass, mock_states):
        """Test that _validate_input returns error for zero time to open."""
        config_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: 0.0,  # Invalid zero time
            CONF_TIME_TO_CLOSE: 25.0,
        }

        errors = _validate_input(hass, config_data)

        assert CONF_TIME_TO_OPEN in errors
        assert errors[CONF_TIME_TO_OPEN] == "invalid_time"

    def test_validate_input_with_invalid_time_to_close_returns_error(self, hass, mock_states):
        """Test that _validate_input returns error for invalid time to close."""
        config_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: -10.0,  # Invalid negative time
        }

        errors = _validate_input(hass, config_data)

        assert CONF_TIME_TO_CLOSE in errors
        assert errors[CONF_TIME_TO_CLOSE] == "invalid_time"

    def test_validate_input_with_invalid_threshold_returns_error(self, hass, mock_states):
        """Test that _validate_input returns error for invalid threshold."""
        config_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
            CONF_THRESHOLD: 150,  # Invalid > 100
        }

        errors = _validate_input(hass, config_data)

        assert CONF_THRESHOLD in errors
        assert errors[CONF_THRESHOLD] == "invalid_threshold"

    def test_validate_input_with_negative_threshold_returns_error(self, hass, mock_states):
        """Test that _validate_input returns error for negative threshold."""
        config_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
            CONF_THRESHOLD: -10,  # Invalid negative
        }

        errors = _validate_input(hass, config_data)

        assert CONF_THRESHOLD in errors
        assert errors[CONF_THRESHOLD] == "invalid_threshold"

    def test_validate_input_allows_optional_sensors_to_be_missing(self, hass, mock_states):
        """Test that _validate_input allows missing optional sensors."""
        config_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
            # No sensors provided
        }

        errors = _validate_input(hass, config_data)

        # Should have no errors for missing optional sensors
        assert CONF_OPEN_SENSOR not in errors
        assert CONF_CLOSED_SENSOR not in errors

    def test_validate_input_with_minimal_valid_data_returns_no_errors(self, hass, mock_states, mock_entity_registry):
        """Test that _validate_input works with minimal valid data."""
        hass.helpers.entity_registry.async_get = mock_entity_registry
        config_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
            CONF_THRESHOLD: DEFAULT_THRESHOLD,
        }

        errors = _validate_input(hass, config_data)

        assert errors == {}


class TestAutoCoverConfigFlowIntegration:
    """Integration tests for the Auto Cover config flow."""

    async def test_config_flow_with_valid_data_creates_entry(self, hass, mock_states, mock_entity_registry):
        """Test that the config flow creates an entry with valid data."""
        hass.helpers.entity_registry.async_get = mock_entity_registry

        # Mock the flow handler
        flow = AutoCoverConfigFlow()
        flow.hass = hass

        # Test data
        test_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
            CONF_OPEN_SENSOR: "binary_sensor.open_sensor",
            CONF_CLOSED_SENSOR: "binary_sensor.closed_sensor",
            CONF_THRESHOLD: DEFAULT_THRESHOLD,
        }

        # Test the step
        result = await flow.async_step_user(test_data)

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Auto Cover - Test Button"
        assert result["data"] == test_data

    async def test_config_flow_with_button_friendly_name_creates_proper_title(self, hass, mock_states, mock_entity_registry):
        """Test that the config flow uses button friendly name in title."""
        hass.helpers.entity_registry.async_get = mock_entity_registry

        # Create button state with friendly name
        button_state = mock_states.states.get("button.test_button")
        button_state.attributes = {"friendly_name": "My Garage Door Button"}

        flow = AutoCoverConfigFlow()
        flow.hass = hass

        test_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
        }

        result = await flow.async_step_user(test_data)

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Auto Cover - My Garage Door Button"

    async def test_config_flow_with_button_without_friendly_name_creates_fallback_title(self, hass, mock_states, mock_entity_registry):
        """Test that the config flow creates fallback title when no friendly name."""
        hass.helpers.entity_registry.async_get = mock_entity_registry

        # Remove friendly name from button state
        button_state = mock_states.states.get("button.test_button")
        button_state.attributes = {}

        flow = AutoCoverConfigFlow()
        flow.hass = hass

        test_data = {
            CONF_BUTTON_ENTITY: "button.garage_door_opener",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
        }

        result = await flow.async_step_user(test_data)

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Auto Cover - Garage Door Opener"

    async def test_config_flow_with_invalid_data_shows_form_with_errors(self, hass, mock_entity_registry):
        """Test that the config flow shows form with errors for invalid data."""
        hass.helpers.entity_registry.async_get = mock_entity_registry
        mock_entity_registry.async_get.return_value = None
        hass.states.async_entity_ids.return_value = []

        flow = AutoCoverConfigFlow()
        flow.hass = hass

        # Invalid data - non-existent button
        test_data = {
            CONF_BUTTON_ENTITY: "button.nonexistent",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
        }

        result = await flow.async_step_user(test_data)

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] is not None
        assert CONF_BUTTON_ENTITY in result["errors"]

    async def test_config_flow_prevents_duplicate_button_entity(self, hass, mock_states, mock_entity_registry):
        """Test that the config flow prevents duplicate button entities."""
        hass.helpers.entity_registry.async_get = mock_entity_registry

        flow = AutoCoverConfigFlow()
        flow.hass = hass

        # First entry
        test_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
        }

        result1 = await flow.async_step_user(test_data)
        assert result1["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY

        # Try to create duplicate entry
        flow2 = AutoCoverConfigFlow()
        flow2.hass = hass

        # Mock that the unique ID is already configured
        with pytest.raises(config_entries.ConfigEntry) as exc_info:
            flow2._abort_if_unique_id_configured = pytest.raises(
                config_entries.ConfigEntry,
                match="already_configured"
            )

            await flow2.async_step_user(test_data)

    async def test_config_flow_handles_missing_optional_sensors_gracefully(self, hass, mock_states, mock_entity_registry):
        """Test that config flow works without optional sensors."""
        hass.helpers.entity_registry.async_get = mock_entity_registry

        flow = AutoCoverConfigFlow()
        flow.hass = hass

        # Data without optional sensors
        test_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
            CONF_THRESHOLD: DEFAULT_THRESHOLD,
        }

        result = await flow.async_step_user(test_data)

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"] == test_data

    async def test_config_flow_with_extreme_valid_values(self, hass, mock_states, mock_entity_registry):
        """Test that config flow handles extreme but valid values."""
        hass.helpers.entity_registry.async_get = mock_entity_registry

        flow = AutoCoverConfigFlow()
        flow.hass = hass

        # Extreme but valid values
        test_data = {
            CONF_BUTTON_ENTITY: "button.test_button",
            CONF_TIME_TO_OPEN: 0.1,  # Minimum allowed
            CONF_TIME_TO_CLOSE: 300.0,  # Maximum allowed
            CONF_THRESHOLD: 100,  # Maximum allowed
        }

        result = await flow.async_step_user(test_data)

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"] == test_data

    async def test_config_flow_shows_form_on_initial_load(self, hass, mock_entity_registry):
        """Test that config flow shows form on initial load."""
        hass.helpers.entity_registry.async_get = mock_entity_registry

        flow = AutoCoverConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user()

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert "data_schema" in result

    async def test_config_flow_preserves_user_input_on_error(self, hass, mock_entity_registry):
        """Test that config flow preserves user input when showing errors."""
        hass.helpers.entity_registry.async_get = mock_entity_registry
        mock_entity_registry.async_get.return_value = None
        hass.states.async_entity_ids.return_value = []

        flow = AutoCoverConfigFlow()
        flow.hass = hass

        # Invalid data but with some valid values that should be preserved
        test_data = {
            CONF_BUTTON_ENTITY: "button.nonexistent",
            CONF_TIME_TO_OPEN: 30.0,
            CONF_TIME_TO_CLOSE: 25.0,
            CONF_THRESHOLD: 50,
        }

        result = await flow.async_step_user(test_data)

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        # The form should be shown again with user input preserved
        schema = result["data_schema"]
        assert schema.schema[CONF_TIME_TO_OPEN].default == 30.0
        assert schema.schema[CONF_TIME_TO_CLOSE].default == 25.0
        assert schema.schema[CONF_THRESHOLD].default == 50