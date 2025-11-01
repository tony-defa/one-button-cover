# One Button Cover for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/tony-defa/one-button-cover.svg)](https://github.com/tony-defa/one-button-cover/releases)
[![License](https://img.shields.io/github/license/tony-defa/one-button-cover.svg)](LICENSE)

A Home Assistant custom component that creates a virtual cover entity from a single-button garage door or gate opener. Perfect for simple garage doors that use a toggle button for open/close/stop operations.

## Features

- ✨ **Single Button Control** - Works with garage doors/gates that use one button for all operations
- 🎯 **Intelligent Position Tracking** - Calculates cover position based on timing
- 🛡️ **Obstacle Detection** - Optional sensor integration for safety
- 🎨 **Full Home Assistant Integration** - Native cover entity with position control
- ⚙️ **Easy Configuration** - Simple UI-based setup through Home Assistant
- 🔄 **Smart Direction Handling** - Automatically manages toggle button behavior

## How It Works

The One Button Cover component transforms a simple toggle button (like those found on garage door openers) into a full-featured cover entity in Home Assistant. It:

1. **Tracks Position**: Uses configurable timing to calculate the cover's current position (0-100%)
2. **Manages Button Presses**: Intelligently handles the toggle behavior:
   - First press: Starts opening/closing
   - Press during movement: Stops the cover
   - Next press: Continues in the last direction
3. **Detects Obstacles**: Optional contact sensors verify position and detect obstacles
4. **Provides Full Control**: Set specific positions, stop at any point, or fully open/close

### Button Behavior

The component handles the complex toggle logic of single-button garage doors:

```
Closed → Press → Opening → Press → Stopped → Press → Closing → Press → Stopped → ...
```

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL
6. Select "Integration" as the category
7. Click "Add"
8. Find "One Button Cover" in the integration list
9. Click "Download"
10. Restart Home Assistant

### Manual Installation

1. Download the `one_button_cover` folder from this repository
2. Copy it to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

### Via UI (Recommended)

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "One Button Cover"
4. Fill in the configuration:
   - **Button Entity**: The button entity that controls your garage door/gate (required)
   - **Time to Open**: Seconds it takes to fully open (required)
   - **Time to Close**: Seconds it takes to fully close (required)
   - **Closed Sensor**: Contact sensor that indicates closed state (optional)
   - **Open Sensor**: Contact sensor that indicates open state (optional)
   - **Threshold**: Safety margin percentage for sensor checks (default: 10%, optional)

### Configuration Example

**Minimal Configuration:**
- Button: `button.garage_door_toggle`
- Time to Open: `30` seconds
- Time to Close: `25` seconds

**Full Configuration with Sensors:**
- Button: `button.garage_door_toggle`
- Time to Open: `30` seconds
- Time to Close: `25` seconds
- Open Sensor: `binary_sensor.garage_door_open`
- Closed Sensor: `binary_sensor.garage_door_closed`
- Threshold: `10%`

## Usage

Once configured, the integration creates a cover entity that appears in Home Assistant with full position control:

### Services

The cover entity supports all standard Home Assistant cover services:

- `cover.open_cover` - Fully open the cover
- `cover.close_cover` - Fully close the cover
- `cover.stop_cover` - Stop the cover at current position
- `cover.set_cover_position` - Set cover to specific position (0-100%)

### Automations

Example automation to open garage when arriving home:

```yaml
automation:
  - alias: "Open Garage on Arrival"
    trigger:
      - platform: zone
        entity_id: person.your_name
        zone: zone.home
        event: enter
    action:
      - service: cover.open_cover
        target:
          entity_id: cover.garage_door
```

### Dashboards

Add to your Lovelace dashboard:

```yaml
type: cover
entity: cover.garage_door
name: Garage Door
```

## How Position Tracking Works

The component calculates the cover's position using timing:

1. **Opening**: Position increases from current position to target over the configured "time to open"
2. **Closing**: Position decreases from current position to target over the configured "time to close"
3. **Partial Positions**: Calculates the exact time needed to reach a specific position

### With Sensors

When contact sensors are configured:
- **Verification**: Sensors verify that the cover reached the expected position
- **Obstacle Detection**: If sensors don't match expectations, an obstacle is detected
- **Manual Operation**: Sensors detect if the cover was operated manually
- **Position Correction**: Automatically corrects position based on sensor feedback

### Without Sensors

The component works perfectly fine without sensors using pure timing-based tracking. Sensors are highly recommended for:
- Obstacle detection
- Position verification
- Manual operation detection
- Improved reliability

## Safety Features

- ✅ **Debounce Protection**: Prevents rapid command spam
- ✅ **Failure Detection**: Disables after multiple consecutive failures
- ✅ **Obstacle Response**: Stops immediately when obstacles detected
- ✅ **Manual Operation**: Tracks and adapts to manual button presses
- ✅ **State Recovery**: Restores position after Home Assistant restart

## Diagnostics

The cover entity provides detailed diagnostic information through attributes:

- `current_position` - Current position (0-100%)
- `next_direction` - Direction of next button press (UP/DOWN)
- `operation_mode` - Sensor configuration (full_sensors/single_sensor/no_sensors)
- `button_entity` - Configured button entity
- `obstacle_detected_count` - Number of obstacles detected
- `manual_operation_count` - Number of manual operations detected
- `time_to_open` - Configured opening time
- `time_to_close` - Configured closing time

## Troubleshooting

### Cover doesn't respond
- Check that the button entity is working correctly
- Verify the button entity ID is correct in the configuration
- Check Home Assistant logs for errors

### Position is inaccurate
- Recalibrate the timing values (time to open/close)
- Add contact sensors for verification
- Check if manual operations are interfering

### Integration is disabled
- This happens after 3 consecutive button press failures
- Check that the button entity is accessible
- Reload the integration to re-enable

### Architecture

The component follows Home Assistant best practices with:
- Clean separation of concerns
- Comprehensive error handling  
- Full test coverage
- Detailed logging
- State persistence

For a detailed context that can be added to an AI Assistant, see [`context.md`](context.md).

### Testing

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_cover.py -v
```

## Credits

- **Developer**: @tony-defa
- **AI Assistant**: Developed with assistance from RooCode and Claude by Anthropic, MiniMax M2 by MiniMax
- **Inspiration**: Born from the need to integrate simple garage door openers into Home Assistant

## License

This project is licensed under the GNU GPLv3 License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review existing [Issues](https://github.com/tony-defa/one-button-cover/issues)
3. Create a new issue with:
   - Home Assistant version
   - Integration version
   - Detailed description of the problem
   - Relevant logs

Not sure if I can immediately help with any issues created, but I'll do my best! 

## Thank You

Thank you for using One Button Cover! Enjoy seamless garage door control with Home Assistant.

