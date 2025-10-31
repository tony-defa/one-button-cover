# One Button Cover Integration Test Suite

This directory contains comprehensive tests for the Home Assistant One Button Cover integration. The test suite validates all functionality and ensures robustness of the virtual cover entity implementation.

## Overview

The One Button Cover integration creates a virtual cover entity from a button entity and optional contact sensors. This test suite covers:

- **Config Flow Validation** - Input validation, schema handling, and configuration management
- **Cover Entity Operations** - Basic operations (open, close, stop, set position) and state management
- **Obstacle Detection** - Sensor-based obstacle detection with configurable thresholds
- **Safety Mechanisms** - Retry limits, stuck detection, and auto-disable functionality
- **Edge Cases** - Error scenarios, rapid commands, and boundary conditions

## Test Files

### `conftest.py` - Test Fixtures and Setup
Common pytest fixtures and test utilities used across all test files:

- **Mock Home Assistant Instance** - Complete HA mock with states, services, and config entries
- **Mock Configuration Entries** - Both full and minimal configuration scenarios
- **Mock Entities** - Button and sensor entities with proper state objects
- **Mock Services** - Service call mocking for button press operations
- **Time Mocking** - Deterministic time handling for timing-sensitive tests
- **Entity Registry** - Mock entity registry for validation tests

### `test_config_flow.py` - Configuration Flow Tests
Tests for the configuration flow implementation:

- **Schema Validation** - Proper voluptuous schema creation and validation
- **Input Validation** - Entity validation, time validation, threshold validation
- **User Flow Testing** - Complete config flow user interactions
- **Edge Case Handling** - Invalid entities, boundary values, duplicate prevention
- **Error Scenarios** - Missing entities, invalid formats, validation failures

**Key Test Scenarios:**
- Valid configuration data creates entry successfully
- Invalid button entity format returns appropriate error
- Missing optional sensors are handled gracefully
- Duplicate button entities are prevented
- Extreme but valid timing values are accepted

### `test_cover.py` - Core Cover Entity Tests
Comprehensive tests for the main OneButtonCover entity class:

- **Initialization** - Proper entity setup with configuration parameters
- **Properties** - Current position, state properties, device info, attributes
- **Basic Operations** - Open, close, stop, set position functionality
- **State Management** - State transitions and validation
- **Position Tracking** - Accurate position updates during movement
- **Button Integration** - Button press coordination and timing
- **Debouncing** - Rapid command filtering and timing
- **State Restoration** - Recovery from restarts and power loss

**Key Test Scenarios:**
- Cover opens/closes from different starting positions
- Position tracking accuracy during movement
- Command debouncing prevents button wear
- State restoration maintains position after restart
- All properties return correct values in all states

### `test_obstacle_detection.py` - Obstacle Detection Tests
Tests for sensor-based obstacle detection:

- **Sensor Integration** - Both sensors required for obstacle detection
- **Threshold Timing** - Configurable obstacle detection timing
- **Movement States** - Obstacle detection during opening/closing
- **Obstacle Handling** - Proper response to detected obstacles
- **Sensor Synchronization** - Position updates from sensor states
- **Manual Operation Detection** - Unexpected sensor changes during movement

**Key Test Scenarios:**
- Obstacle detected when both sensors trigger during movement
- Single sensor trigger doesn't cause false obstacle detection
- Obstacle check timing based on movement progress and threshold
- Manual operation counter increments on unexpected changes
- Position synchronization from conflicting sensors

### `test_safety.py` - Safety Mechanism Tests
Tests for safety and reliability features:

- **Retry Limits** - Maximum retry enforcement and failure tracking
- **Auto-Disable** - Cover disabling after consecutive failures
- **Stuck Detection** - Movement timeout and stuck condition handling
- **State Restoration** - Safe state recovery after power loss
- **Error Recovery** - Graceful handling of various error conditions
- **Safety Logging** - Proper logging of safety events

**Key Test Scenarios:**
- Cover disables after maximum consecutive failures
- Stuck detection triggers after timeout with no position change
- Power loss during movement converts to safe halted state
- Failed operations increment failure counter appropriately
- Safety events are logged with proper context

### `test_edge_cases.py` - Edge Cases and Error Tests
Tests for unusual scenarios and error conditions:

- **Rapid Commands** - High-frequency command handling
- **Sensor Failures** - Unavailable or malfunctioning sensors
- **Direction Changes** - Mid-movement direction changes
- **Manual Operation** - Manual override during automatic movement
- **Power Loss** - Recovery from power interruption scenarios
- **Resource Management** - Memory and handle cleanup
- **Race Conditions** - Concurrent access and timing issues
- **Environmental Stress** - Extreme timing and position values

**Key Test Scenarios:**
- Rapid button presses are properly debounced
- Sensor unavailability during operation is handled gracefully
- Direction changes mid-movement are executed safely
- Power loss during movement results in safe state restoration
- Resource cleanup prevents memory leaks
- Race conditions don't cause state corruption

## Running Tests

### Prerequisites
- Python 3.8+
- Home Assistant development environment
- Required test dependencies (pytest, pytest-homeassistant-custom-component)

### Installation
```bash
# Install test dependencies
pip install pytest pytest-homeassistant-custom-component pytest-asyncio freezegun

# Optional: Install coverage tools
pip install pytest-cov coverage[toml]
```

### Execution
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_cover.py

# Run with coverage
pytest tests/ --cov=custom_components.one_button_cover --cov-report=html

# Run with verbose output
pytest tests/ -v

# Run specific test class or method
pytest tests/test_cover.py::TestOneButtonCoverBasicOperations::test_open_cover_from_closed_state -v
```

### Test Configuration
Tests use the virtual environment in `.env/` folder as specified:
```bash
# Use the virtual environment
source .env/bin/activate
pytest tests/
```

## Test Coverage Areas

### Functionality Coverage
- ✅ **Configuration Flow** - Complete validation and user flow testing
- ✅ **Basic Operations** - All cover operations (open, close, stop, set position)
- ✅ **Position Tracking** - Accurate position calculation during movement
- ✅ **State Management** - All state transitions and validations
- ✅ **Button Integration** - Button press timing and coordination
- ✅ **Obstacle Detection** - Dual-sensor obstacle detection with thresholds
- ✅ **Safety Mechanisms** - Retry limits, stuck detection, auto-disable
- ✅ **Error Handling** - Graceful failure handling and recovery
- ✅ **Edge Cases** - Unusual scenarios and boundary conditions

### Code Coverage Target
The test suite aims for >90% code coverage of the integration code:

- **Cover Entity** - All methods and properties thoroughly tested
- **Config Flow** - All validation paths and error conditions
- **Constants** - All configuration values and enums validated
- **Error Paths** - Exception handling and edge cases covered

## Test Design Principles

### Mocking Strategy
- **Minimal Mocking** - Only mock external dependencies, test actual logic
- **Realistic Data** - Use realistic entity IDs and state values
- **Service Integration** - Mock HA services while testing service calls
- **Time Control** - Use freezegun or similar for deterministic timing

### Test Organization
- **Descriptive Names** - Test methods describe what they validate
- **Arrange-Act-Assert** - Clear test structure following AAA pattern
- **Class Grouping** - Related tests grouped in classes
- **Parametrized Tests** - Similar scenarios use parametrized tests
- **Documentation** - Docstrings explain test purpose and scenarios

### Async Testing
- **Proper Async Handling** - All async methods tested with proper async fixtures
- **Event Loop Management** - Proper event loop handling for async tests
- **Timing Control** - Deterministic time handling for time-sensitive tests
- **Callback Testing** - Proper testing of callback-based functionality

## Test Data and Fixtures

### Common Test Data
- **Entity IDs** - `button.test_button`, `binary_sensor.open_sensor`, `binary_sensor.closed_sensor`
- **Timing Values** - 30s open, 25s close (realistic garage door timing)
- **Threshold** - 10% (default obstacle detection threshold)
- **Position Values** - 0, 25, 50, 75, 100 (common cover positions)

### Fixture Categories
- **Entity Fixtures** - Mock entities with proper HA state objects
- **Service Fixtures** - Mock service calls for button operations
- **Time Fixtures** - Deterministic time for timing-sensitive tests
- **Configuration Fixtures** - Various configuration scenarios

## Debugging Tests

### Common Issues
- **Import Errors** - Ensure all dependencies are installed in virtual environment
- **Async Issues** - Make sure event loop is properly configured
- **Mock Issues** - Verify mocks don't interfere with actual code paths
- **Timing Issues** - Use deterministic time mocking for reproducible tests

### Debug Commands
```bash
# Run tests with debug output
pytest tests/ -v -s --tb=short

# Run specific failing test with detailed output
pytest tests/test_cover.py::TestOneButtonCoverBasicOperations::test_open_cover_from_closed_state -v -s --tb=long

# Check test coverage
pytest tests/ --cov=custom_components.one_button_cover --cov-report=term-missing

# Run tests in specific order
pytest tests/ --setup-plan
```

## CI/CD Integration

### Automated Testing
The test suite is designed to run in CI/CD pipelines:

```bash
# Basic CI test command
pytest tests/ --tb=short -q

# Coverage reporting for CI
pytest tests/ --cov=custom_components.one_button_cover --cov-report=xml --cov-report=term

# Fail build on low coverage
pytest tests/ --cov=custom_components.one_button_cover --cov-fail-under=90
```

### Test Parallelization
Tests can be run in parallel for faster execution:
```bash
# Run tests in parallel
pytest tests/ -n auto

# Run specific test files in parallel
pytest tests/test_cover.py tests/test_config_flow.py -n auto
```

## Contributing

### Adding New Tests
1. Follow existing test patterns and naming conventions
2. Add appropriate fixtures to `conftest.py` if needed
3. Ensure tests are isolated and don't depend on test order
4. Add docstrings explaining test scenarios
5. Update this README if adding new test categories

### Test Maintenance
- Keep mocks up to date with HA API changes
- Update test data when default values change
- Ensure tests pass with latest HA versions
- Maintain >90% code coverage target

## Troubleshooting

### Common Test Failures
- **Module Not Found** - Ensure all dependencies are installed
- **Async Event Loop** - Make sure tests are properly marked as async
- **Mock Interference** - Verify mocks don't affect other tests
- **Time Sensitivity** - Use deterministic time mocking for timing tests

### Performance Issues
- **Slow Tests** - Optimize expensive fixtures and mocks
- **Memory Usage** - Clean up resources in fixture teardown
- **CI Timeouts** - Split large test files or optimize test execution

## Version History

- **v1.0** - Initial comprehensive test suite
- **Coverage** - >90% code coverage target
- **CI Integration** - Automated testing in CI/CD pipelines
- **Edge Case Coverage** - Comprehensive error scenario testing

---

For questions or issues with the test suite, please refer to the main integration documentation or create an issue in the project repository.