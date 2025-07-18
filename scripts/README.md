# Utility Scripts

This directory contains utility scripts for various system operations, maintenance, and data management tasks.

## Script Categories

### Device Management
- `ava4_offline_monitor.py` - Monitor AVA4 device offline status
- `ava4_status_monitor.py` - Monitor AVA4 device status
- `check_amy_devices.py` - Check AMY devices in database
- `check_ava4_payload_structure.py` - Validate AVA4 payload structure
- `check_ava4_raw_data.py` - Check AVA4 raw data
- `check_ble_device_mapping.py` - Check BLE device mappings
- `check_ble_mapping_api.py` - Test BLE mapping API
- `check_device_mapping_simple.py` - Simple device mapping check
- `check_device_owner.py` - Check device ownership
- `check_patient_name.py` - Check patient name data
- `find_ava4_device.py` - Find AVA4 devices
- `register_device.py` - Register new devices

### Database Management
- `check_database_structure.py` - Check database schema
- `fix_amy_devices_mapping.py` - Fix AMY device mappings
- `fix_device_database.py` - Fix device database issues
- `fix_device_mapping.py` - Fix device mapping issues
- `fix_device_mapping_database.py` - Fix device mapping database
- `fix_sub_device_mapping.py` - Fix sub-device mappings
- `fix_sub_device_mapping_v2.py` - Enhanced sub-device mapping fixes
- `lookup_patient_names.py` - Lookup patient names
- `remove_mock_data.py` - Remove mock/test data

### Data Processing
- `clean_coruscant_mock_data.py` - Clean Coruscant mock data
- `clean_mock_data.py` - Clean mock data
- `fetch_test_data.py` - Fetch test data
- `medical_data_monitor.py` - Monitor medical data
- `monitor_complete_data_flow.py` - Monitor complete data flow
- `mqtt_realtime_monitor.py` - Real-time MQTT monitoring
- `send_ava4_payload.py` - Send AVA4 test payloads
- `update_ava4_data.py` - Update AVA4 data
- `verify_mqtt_capture.py` - Verify MQTT data capture

### Documentation & API
- `fix_all_duplicate_tags.py` - Fix all duplicate Swagger tags
- `fix_duplicate_tags.py` - Fix duplicate Swagger tags
- `fix_swagger_duplicate_tags.py` - Fix Swagger duplicate tags
- `update_app_openapi.py` - Update app OpenAPI specification
- `update_postman_collection.py` - Update Postman collections
- `update_swagger_documentation.py` - Update Swagger documentation
- `update_swagger_with_new_endpoints.py` - Update Swagger with new endpoints

### Docker & Deployment
- `docker_medical_monitor.py` - Docker medical monitor setup

## Usage

Most scripts can be run directly:
```bash
python scripts/script_name.py
```

Some scripts may require specific parameters or environment setup. Check individual script headers for usage instructions.

## Script Dependencies

Scripts may depend on:
- Database connection (MongoDB/PostgreSQL)
- MQTT broker connection
- API endpoints
- Configuration files

Ensure the main application environment is properly configured before running scripts. 