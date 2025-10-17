"""Config flow for Auto Cover integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import (
    CONF_BUTTON_ENTITY,
    CONF_CLOSED_SENSOR,
    CONF_OPEN_SENSOR,
    CONF_THRESHOLD,
    CONF_TIME_TO_CLOSE,
    CONF_TIME_TO_OPEN,
    DEFAULT_THRESHOLD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _get_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    """Get the data schema for the config flow.
    
    Args:
        user_input: Optional user input to pre-populate the form.
        
    Returns:
        The voluptuous schema for the configuration form.
    """
    if user_input is None:
        user_input = {}

    return vol.Schema(
        {
            vol.Required(
                CONF_BUTTON_ENTITY,
                default=user_input.get(CONF_BUTTON_ENTITY, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="button"),
            ),
            vol.Optional(
                CONF_CLOSED_SENSOR,
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="binary_sensor",
                    multiple=False,
                ),
            ),
            vol.Optional(
                CONF_OPEN_SENSOR,
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="binary_sensor",
                    multiple=False,
                ),
            ),
            vol.Required(
                CONF_TIME_TO_OPEN,
                default=user_input.get(CONF_TIME_TO_OPEN, 30),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1,
                    max=300,
                    step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="seconds",
                ),
            ),
            vol.Required(
                CONF_TIME_TO_CLOSE,
                default=user_input.get(CONF_TIME_TO_CLOSE, 30),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1,
                    max=300,
                    step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="seconds",
                ),
            ),
            vol.Optional(
                CONF_THRESHOLD,
                default=user_input.get(CONF_THRESHOLD, DEFAULT_THRESHOLD),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="%",
                ),
            ),
        }
    )


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate the user input.
    
    Args:
        hass: Home Assistant instance.
        data: The configuration data to validate.
        
    Returns:
        Dictionary of validation errors (empty if no errors).
    """
    errors: dict[str, str] = {}
    entity_registry = async_get_entity_registry(hass)

    # Validate button entity
    button_entity = data.get(CONF_BUTTON_ENTITY)
    if button_entity:
        if not button_entity.startswith("button."):
            errors[CONF_BUTTON_ENTITY] = "invalid_entity"
        else:
            # Check if entity exists
            entity = entity_registry.async_get(button_entity)
            if entity is None and button_entity not in hass.states.async_entity_ids():
                errors[CONF_BUTTON_ENTITY] = "invalid_entity"
    else:
        errors[CONF_BUTTON_ENTITY] = "invalid_entity"

    # Validate closed sensor (optional)
    closed_sensor = data.get(CONF_CLOSED_SENSOR)
    if closed_sensor:
        if not closed_sensor.startswith("binary_sensor."):
            errors[CONF_CLOSED_SENSOR] = "invalid_entity"
        else:
            entity = entity_registry.async_get(closed_sensor)
            if entity is None and closed_sensor not in hass.states.async_entity_ids():
                errors[CONF_CLOSED_SENSOR] = "invalid_entity"

    # Validate open sensor (optional)
    open_sensor = data.get(CONF_OPEN_SENSOR)
    if open_sensor:
        if not open_sensor.startswith("binary_sensor."):
            errors[CONF_OPEN_SENSOR] = "invalid_entity"
        else:
            entity = entity_registry.async_get(open_sensor)
            if entity is None and open_sensor not in hass.states.async_entity_ids():
                errors[CONF_OPEN_SENSOR] = "invalid_entity"

    # Validate time to open
    time_to_open = data.get(CONF_TIME_TO_OPEN)
    if time_to_open is None or time_to_open <= 0:
        errors[CONF_TIME_TO_OPEN] = "invalid_time"

    # Validate time to close
    time_to_close = data.get(CONF_TIME_TO_CLOSE)
    if time_to_close is None or time_to_close <= 0:
        errors[CONF_TIME_TO_CLOSE] = "invalid_time"

    # Validate threshold
    threshold = data.get(CONF_THRESHOLD, DEFAULT_THRESHOLD)
    if threshold < 0 or threshold > 100:
        errors[CONF_THRESHOLD] = "invalid_threshold"

    return errors


class AutoCoverConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Auto Cover integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step of the config flow.
        
        Args:
            user_input: The user's input data, or None for the initial form.
            
        Returns:
            The flow result (form or create entry).
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Remove empty sensor values to make them truly optional
            if CONF_CLOSED_SENSOR in user_input and not user_input[CONF_CLOSED_SENSOR]:
                user_input.pop(CONF_CLOSED_SENSOR)
            if CONF_OPEN_SENSOR in user_input and not user_input[CONF_OPEN_SENSOR]:
                user_input.pop(CONF_OPEN_SENSOR)
            
            # Validate input
            errors = await _validate_input(self.hass, user_input)

            if not errors:
                # Check for duplicate entries (same button entity)
                await self.async_set_unique_id(user_input[CONF_BUTTON_ENTITY])
                self._abort_if_unique_id_configured()

                # Get the button entity's friendly name for the entry title
                button_entity_id = user_input[CONF_BUTTON_ENTITY]
                button_state = self.hass.states.get(button_entity_id)
                
                if button_state and button_state.attributes.get("friendly_name"):
                    title = f"Auto Cover - {button_state.attributes['friendly_name']}"
                else:
                    # Fallback to entity ID if friendly name not available
                    title = f"Auto Cover - {button_entity_id.split('.')[1].replace('_', ' ').title()}"

                # Create the config entry
                return self.async_create_entry(
                    title=title,
                    data=user_input,
                )

        # Show the form (initial or with errors)
        return self.async_show_form(
            step_id="user",
            data_schema=_get_schema(user_input),
            errors=errors,
        )