"""The Auto Cover integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.COVER]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Auto Cover component.
    
    This function handles the legacy YAML-based setup.
    Since this integration uses config flow, this always returns True.
    
    Args:
        hass: Home Assistant instance
        config: Configuration dictionary
        
    Returns:
        bool: Always returns True to indicate successful setup
    """
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Auto Cover from a config entry.
    
    This function is called when a config entry is loaded.
    It forwards the setup to the cover platform.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry to set up
        
    Returns:
        bool: True if setup was successful
    """
    _LOGGER.debug("Setting up Auto Cover entry: %s", entry.entry_id)
    
    # Forward entry setup to the cover platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.
    
    This function is called when a config entry is being removed.
    It unloads the cover platform and cleans up resources.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry to unload
        
    Returns:
        bool: True if unload was successful
    """
    _LOGGER.debug("Unloading Auto Cover entry: %s", entry.entry_id)
    
    # Unload the cover platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    return unload_ok