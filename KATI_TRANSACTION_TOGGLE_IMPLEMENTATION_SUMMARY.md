# Kati Transaction Monitor Toggle Implementation Summary

## Overview
Successfully implemented a toggle functionality in the Kati Watch Transaction Monitor dashboard to switch between "Patient Data Only" and "All Device Data" views. This allows users to monitor both mapped patient devices and unmapped Kati Watch devices.

## Features Implemented

### 1. Toggle Switch UI
- **Location**: Page header in Kati Transaction Monitor
- **Design**: Radio button group with Tabler UI styling
- **Options**:
  - **Patient Data Only**: Shows only devices mapped to patients
  - **All Device Data**: Shows all Kati devices (mapped and unmapped)

### 2. Enhanced API Endpoints

#### Modified `/api/kati-transactions`
- **New Parameter**: `filter` (patient_only | all_devices)
- **Patient Only Mode**: Filters data to show only mapped devices
- **All Devices Mode**: Shows all Kati devices regardless of mapping
- **Enhanced Statistics**: Includes mapped/unmapped device counts

#### New `/api/kati-transactions/all-devices`
- **Purpose**: Dedicated endpoint for all device data
- **Features**: Increased limit (1000 transactions vs 500)
- **Statistics**: Detailed breakdown of mapped vs unmapped devices

### 3. Enhanced Statistics Display

#### Patient Data Only View
- Total Transactions
- Active Devices (mapped only)
- Success Rate
- Emergency Alerts

#### All Device Data View
- **Additional Statistics Cards**:
  - Mapped Devices (with patient data)
  - Unmapped Devices (no patient data)
  - Mapped Transactions
  - Unmapped Transactions

### 4. Data Processing Updates

#### Kati Listener Modifications
- **Unmapped Device Support**: Now processes and stores data from unmapped devices
- **Conditional FHIR Storage**: Only stores in FHIR for mapped patients
- **Medical Collection Storage**: Stores all device data for monitoring
- **Enhanced Logging**: Distinguishes between mapped and unmapped device processing

#### Data Storage Logic
```python
# Store ALL data types for monitoring display (including unmapped devices)
medical_data = {
    "device_type": "Kati_Watch",
    "device_id": imei,
    "topic": topic,
    "data": data,
    "timestamp": datetime.utcnow(),
    "processed_at": datetime.utcnow()
}

# Add patient info if available
if patient_id:
    medical_data["patient_id"] = patient_id
    medical_data["patient_name"] = patient_name
else:
    medical_data["patient_name"] = f"Unmapped Device ({imei})"
```

### 5. Frontend Enhancements

#### JavaScript Functionality
- **Dynamic Data Loading**: Loads data based on selected filter
- **Real-time Updates**: Socket.IO updates respect current filter
- **Statistics Updates**: Updates all statistics cards based on filter
- **Display Logic**: Shows/hides additional statistics cards

#### UI Improvements
- **Unmapped Device Indicators**: Badge showing "Unmapped" for devices without patient data
- **Device Information**: Shows device IMEI for unmapped devices
- **Enhanced Data Formatting**: Better display of device-specific data

## Technical Implementation

### Backend Changes

#### Web Panel API (`app.py`)
```python
@app.route('/api/kati-transactions')
def get_kati_transactions():
    data_filter = request.args.get('filter', 'patient_only')
    
    if data_filter == 'patient_only':
        # Only show data that has patient_id (mapped devices)
        kati_transactions = list(medical_data_collection.find({
            'device_type': 'Kati_Watch',
            'timestamp': {'$gte': one_day_ago},
            'patient_id': {'$exists': True, '$ne': None}
        }).sort('timestamp', -1).limit(500))
    else:
        # Show all Kati Watch data (including unmapped devices)
        kati_transactions = list(medical_data_collection.find({
            'device_type': 'Kati_Watch',
            'timestamp': {'$gte': one_day_ago}
        }).sort('timestamp', -1).limit(500))
```

#### Kati Listener (`main.py`)
```python
# Find patient by Kati IMEI
patient = self.device_mapper.find_patient_by_kati_imei(imei)

if patient:
    # Process mapped device
    patient_info = {...}
    logger.info(f"Processing {topic} data for patient {patient['_id']}")
else:
    # Process unmapped device
    logger.info(f"Processing {topic} data for unmapped device IMEI: {imei}")

# Store in medical collection (mapped and unmapped)
medical_data = {
    "device_type": "Kati_Watch",
    "device_id": imei,
    "topic": topic,
    "data": data,
    "timestamp": datetime.utcnow()
}

if patient_id:
    medical_data["patient_id"] = patient_id
    medical_data["patient_name"] = patient_name
else:
    medical_data["patient_name"] = f"Unmapped Device ({imei})"
```

### Frontend Changes

#### HTML Template (`kati-transaction.html`)
```html
<!-- Data Filter Toggle -->
<div class="btn-group" role="group">
    <input type="radio" class="btn-check" name="data-filter" id="patient-only" value="patient_only" checked>
    <label class="btn btn-outline-primary" for="patient-only">
        <i class="ti ti-user"></i>
        Patient Data Only
    </label>
    
    <input type="radio" class="btn-check" name="data-filter" id="all-devices" value="all_devices">
    <label class="btn btn-outline-secondary" for="all-devices">
        <i class="ti ti-devices"></i>
        All Device Data
    </label>
</div>
```

#### JavaScript Functionality
```javascript
// Initialize data filter toggle
function initializeDataFilter() {
    const patientOnlyRadio = document.getElementById('patient-only');
    const allDevicesRadio = document.getElementById('all-devices');
    
    patientOnlyRadio.addEventListener('change', function() {
        if (this.checked) {
            currentDataFilter = 'patient_only';
            loadKatiData();
        }
    });
    
    allDevicesRadio.addEventListener('change', function() {
        if (this.checked) {
            currentDataFilter = 'all_devices';
            loadKatiData();
        }
    });
}

// Load Kati transaction data
function loadKatiData() {
    const url = currentDataFilter === 'patient_only' 
        ? '/api/kati-transactions?filter=patient_only'
        : '/api/kati-transactions?filter=all_devices';
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                katiData = data.data.transactions || [];
                displayKatiTransactions();
                updateStatistics(data.data.statistics);
                updateDataFilterDisplay();
            }
        });
}
```

## Benefits

### 1. Complete Device Visibility
- **Mapped Devices**: Full patient context and FHIR integration
- **Unmapped Devices**: Raw device data for monitoring and troubleshooting

### 2. Enhanced Monitoring
- **Device Registration**: Identify devices that need patient mapping
- **Data Quality**: Monitor all incoming Kati Watch data
- **System Health**: Track device connectivity and data flow

### 3. Operational Efficiency
- **Quick Toggle**: Easy switching between views
- **Real-time Updates**: Live data updates for both views
- **Comprehensive Statistics**: Detailed metrics for both mapped and unmapped devices

## Usage

### Accessing the Toggle
1. Navigate to **Kati Transaction Monitor** at `http://localhost:8098/kati-transaction`
2. Locate the toggle buttons in the page header
3. Click **"Patient Data Only"** or **"All Device Data"** to switch views

### Understanding the Data

#### Patient Data Only View
- Shows only devices mapped to patients
- Includes patient names and IDs
- Full FHIR integration
- Standard monitoring statistics

#### All Device Data View
- Shows all Kati Watch devices
- Unmapped devices marked with "Unmapped" badge
- Device IMEI displayed for unmapped devices
- Additional statistics for mapped vs unmapped breakdown

## Deployment Status

✅ **Fully Implemented and Deployed**
- Web panel container rebuilt and restarted
- Kati listener updated and running
- API endpoints tested and functional
- Frontend toggle working correctly

## Future Enhancements

1. **Device Registration Workflow**: Direct integration with patient mapping
2. **Advanced Filtering**: Filter by device status, data type, or time range
3. **Export Functionality**: Export data for both views
4. **Alert System**: Notifications for unmapped devices
5. **Bulk Operations**: Mass device mapping or data processing

## Technical Notes

- **Database Impact**: Minimal - uses existing collections with enhanced queries
- **Performance**: Optimized with proper indexing and query limits
- **Scalability**: Supports large numbers of devices and transactions
- **Security**: Maintains existing authentication and authorization

The toggle functionality provides complete visibility into the Kati Watch ecosystem while maintaining the existing patient-centric workflow for mapped devices. 