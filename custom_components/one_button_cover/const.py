"""Constants for the One Button Cover integration."""
from enum import Enum

# Integration domain
DOMAIN = "one_button_cover"

# Configuration keys
CONF_BUTTON_ENTITY = "button_entity"
CONF_CLOSED_SENSOR = "closed_sensor"
CONF_OPEN_SENSOR = "open_sensor"
CONF_TIME_TO_OPEN = "time_to_open"
CONF_TIME_TO_CLOSE = "time_to_close"
CONF_THRESHOLD = "threshold"

# Default values
DEFAULT_THRESHOLD = 10  # percentage


class CoverState(Enum):
    """Cover state enumeration."""

    CLOSED = "closed"
    OPEN = "open"
    CLOSING = "closing"
    OPENING = "opening"
    HALTED = "halted"


# Button timing constants
BUTTON_ACTIVATION_TIME = 0.5  # seconds
POSITION_UPDATE_INTERVAL = 0.1  # seconds

# Safety constants
MAX_RETRIES = 3

# Debounce time for rapid commands (seconds)
DEBOUNCE_TIME = 0.6