# Test Files

This directory contains test files organized by category for easy maintenance and execution.

## Directory Structure

### scripts/
Contains Python test scripts for various system components:
- API endpoint tests
- Database structure tests
- Device mapping tests
- MQTT payload tests
- Medical data tests
- Web panel display tests

### web-panel/
Contains frontend test files:
- HTML test pages
- JavaScript test files
- Web panel functionality tests

### mqtt/
Contains MQTT-specific test files:
- MQTT connection tests
- AVA4 payload tests
- Device status tests

### medical/
Contains medical monitoring test files:
- Medical data processing tests
- Patient data tests
- Vital signs tests

## Test Categories

### API Testing
- Comprehensive endpoint tests
- CRUD operation tests
- Authentication tests
- Error handling tests

### Device Testing
- Device mapping tests
- AVA4 device tests
- Kati Watch tests
- Qube Vital tests

### Data Flow Testing
- MQTT data processing tests
- Real-time data flow tests
- Event streaming tests

### Web Panel Testing
- Frontend functionality tests
- JavaScript integration tests
- UI component tests

## Running Tests

Most test files can be run directly with Python:
```bash
python tests/scripts/test_file_name.py
```

For web panel tests, open the HTML files in a browser or use a web testing framework. 