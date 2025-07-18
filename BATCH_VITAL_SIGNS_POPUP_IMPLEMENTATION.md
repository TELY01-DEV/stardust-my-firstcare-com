# Batch Vital Signs Popup Implementation

## Overview
Implemented a popup modal feature for the Kati Transaction Monitor to display detailed batch vital signs data with averages when clicking on batch data records.

## Features Implemented

### 1. New API Endpoint
- **Endpoint**: `/api/kati-transactions/<transaction_id>/batch-details`
- **Method**: GET
- **Authentication**: Required
- **Purpose**: Retrieves detailed batch vital signs data for a specific transaction

### 2. Data Processing
- **Batch Data Extraction**: Handles both `vital_signs` and `data` array structures
- **Average Calculations**: 
  - Heart Rate (bpm)
  - Blood Pressure (systolic/diastolic mmHg)
  - Body Temperature (°C)
  - SpO2 (%)
- **Patient Information**: Includes patient details and profile image if available

### 3. Frontend Modal
- **Modal Size**: Extra large (modal-xl) for better data display
- **Loading State**: Shows spinner while fetching data
- **Error Handling**: Displays error messages if data loading fails

### 4. Data Display Sections

#### Patient Information Card
- Patient name and photo
- Device ID
- Batch size
- Timestamp

#### Averages Card
- Heart Rate average
- Blood Pressure average (systolic/diastolic)
- Body Temperature average
- SpO2 average

#### Individual Records Table
- Record number
- Timestamp
- Heart Rate
- Blood Pressure
- Temperature
- SpO2

### 5. User Interface Enhancements
- **Clickable Batch Links**: Batch data text is now clickable with blue underline
- **Responsive Design**: Modal adapts to different screen sizes
- **Bootstrap Styling**: Consistent with existing UI design

## Technical Implementation

### Backend (Flask)
```python
@app.route('/api/kati-transactions/<transaction_id>/batch-details')
@login_required
def get_batch_vital_signs_details(transaction_id):
    # Extracts batch data and calculates averages
    # Returns structured JSON response
```

### Frontend (JavaScript)
```javascript
function viewBatchVitalSigns(transactionId) {
    // Shows modal and fetches data
}

function displayBatchVitalSigns(batchData) {
    // Renders patient info, averages, and data table
}
```

### HTML Modal Structure
```html
<div class="modal fade" id="batchVitalSignsModal">
    <div class="modal-dialog modal-xl">
        <!-- Modal content with patient info, averages, and data table -->
    </div>
</div>
```

## Data Structure Example

### Input (Batch Transaction)
```json
{
  "event_type": "batch_vital_signs",
  "data": {
    "data": [
      {
        "heartRate": 90,
        "bloodPressure": {"bp_sys": 121, "bp_dia": 74},
        "bodyTemperature": 36.8,
        "spO2": 97,
        "timestamp": 1752866715
      }
      // ... more records
    ],
    "num_datas": 10
  }
}
```

### Output (API Response)
```json
{
  "success": true,
  "data": {
    "batch_size": 10,
    "averages": {
      "heartRate": 87.9,
      "bloodPressure": {"systolic": 121.8, "diastolic": 73.9},
      "bodyTemperature": 36.6,
      "spO2": 96.9
    },
    "vital_signs": [...],
    "patient_info": {...}
  }
}
```

## Usage Instructions

1. **Access Kati Transaction Monitor**: Navigate to `/kati-transaction`
2. **Find Batch Data**: Look for "Batch: X vital signs records" in the Data column
3. **Click Batch Link**: Click on the blue underlined batch text
4. **View Details**: Modal opens showing:
   - Patient information
   - Calculated averages
   - Individual vital signs records table

## Deployment Status

- ✅ **API Endpoint**: Implemented and tested
- ✅ **Frontend Modal**: Implemented and styled
- ✅ **Data Processing**: Working correctly
- ✅ **Container**: Rebuilt and restarted
- ✅ **Testing**: API returns correct data structure

## Future Enhancements

1. **Export Functionality**: Add ability to export batch data to CSV/PDF
2. **Charts/Graphs**: Visual representation of vital signs trends
3. **Filtering**: Filter individual records by date range
4. **Comparison**: Compare multiple batch records
5. **Alerts**: Highlight abnormal values in the data

## Files Modified

1. `services/mqtt-monitor/web-panel/app.py` - Added batch details API endpoint
2. `services/mqtt-monitor/web-panel/templates/kati-transaction.html` - Added modal and JavaScript functions

## Testing Results

- ✅ API endpoint returns correct data structure
- ✅ Averages calculated accurately
- ✅ Modal displays properly
- ✅ Patient information included when available
- ✅ Error handling works correctly

The batch vital signs popup feature is now fully operational and ready for use. 