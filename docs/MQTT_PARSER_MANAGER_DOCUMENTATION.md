### Supported Packet Types & Topics

| Packet Type | MQTT Topic | Purpose | Trigger |
|-------------|------------|---------|---------|
| `AP03` | `iMEDE_watch/hb` | Heartbeat/Status | Regular intervals, device status updates |
| `APHP+AP03+AP01+AP02` | `iMEDE_watch/VitalSign` | Vital Signs | Health measurements, monitoring sessions |
| `AP55` | `iMEDE_watch/AP55` | Batch Health Data | Historical data upload, sync operations |
| `AP01+AP02` | `iMEDE_watch/location` | Location Data | GPS updates, location requests |
| `AP97` | `iMEDE_watch/sleepdata` | Sleep Analysis | Sleep period completion, data upload |
| `AP10 (alarm_state='01')` | `iMEDE_watch/sos` | SOS Emergency | SOS button press, manual emergency |
| `AP10 (alarm_state='05'/'06')` | `iMEDE_watch/fallDown` | Fall Detection | Accelerometer fall detection |

### Core Methods

#### `parse_packet_to_mqtt(parsed_packet: Dict[str, Any]) -> Optional[Dict[str, Any]]`
Main entry point for packet processing.

**Parameters:**
- `parsed_packet`: Dictionary containing parsed packet data from the TCP server

**Returns:**
- Dictionary with `topic` and `payload` keys, or None if packet type not supported

**Example:**
```python
parser = MQTTDataParser()
result = parser.parse_packet_to_mqtt({
    'type': 'AP03',
    'IMEI': '865067123456789',
    'battery_level': 67,
    'signal_strength': 80
})
# Returns: {'topic': 'iMEDE_watch/hb', 'payload': '{"IMEI": "865067123456789", ...}'}
```

### Packet-Specific Parsers

#### 1. Heartbeat Parser (`_parse_ap03_heartbeat`)
**Topic:** `iMEDE_watch/hb`

**Payload Structure:**
```json
{
    "IMEI": "865067123456789",
    "signalGSM": 80,
    "battery": 67,
    "satellites": 4,
    "workingMode": 2,
    "timeStamps": "16/06/2025 12:30:45",
    "step": 999
}
```

#### 2. Vital Signs Parser (`_parse_vital_signs`)
**Topic:** `iMEDE_watch/VitalSign`

**Payload Structure:**
```json
{
    "IMEI": "865067123456789",
    "heartRate": 72,
    "bloodPressure": {
        "bp_sys": 122,
        "bp_dia": 74
    },
    "bodyTemperature": 36.6,
    "spO2": 97,
    "signalGSM": 80,
    "battery": 67,
    "location": {
        "GPS": {"latitude": 22.5678, "longitude": 112.3456},
        "WiFi": "[{...}]",
        "LBS": {"MCC": "520", "MNC": "3", "LAC": "1815", "CID": "79474300"}
    },
    "timeStamps": "16/06/2025 12:30:45"
}
```

#### 3. AP55 Dataset Parser (`_parse_ap55_dataset`)
**Topic:** `iMEDE_watch/AP55`

**Payload Structure:**
```json
{
    "IMEI": "865067123456789",
    "location": {...},
    "timeStamps": "16/06/2025 12:30:45",
    "num_datas": 12,
    "data": [
        {
            "timestamp": 1738331256,
            "heartRate": 84,
            "bloodPressure": {"bp_sys": 119, "bp_dia": 73},
            "spO2": 98,
            "bodyTemperature": 36.9
        }
    ]
}
```

#### 4. Location Parser (`_parse_location`)
**Topic:** `iMEDE_watch/location`

**Payload Structure:**
```json
{
    "IMEI": "865067123456789",
    "location": {
        "GPS": {
            "latitude": 22.5678,
            "longitude": 112.3456,
            "speed": 0.0,
            "header": 180.0
        },
        "WiFi": "[{'SSID':'WiFi1','MAC':'aa-bb-cc-dd-ee-ff','RSSI':'87'}]",
        "LBS": {
            "MCC": "520",
            "MNC": "3", 
            "LAC": "1815",
            "CID": "79474300",
            "SetBase": "[{...}]"
        }
    }
}
```

#### 5. Sleep Data Parser (`_parse_sleep_data`)
**Topic:** `iMEDE_watch/sleepdata`

**Payload Structure:**
```json
{
    "IMEI": "865067123456789",
    "sleep": {
        "timeStamps": "16/06/2025 01:00:00",
        "time": "2200@0700",
        "data": "0000000111110000010011111110011111111111110000000002200000001111111112111100111001111111211111111222111111111110110111111110110111111011112201110",
        "num": 145
    }
}
```

#### 6. Emergency Alarm Parser (`_parse_emergency_alarm`)
**Topics:** `iMEDE_watch/sos` or `iMEDE_watch/fallDown`

**SOS Payload:**
```json
{
    "status": "SOS",
    "location": {...},
    "IMEI": "865067123456789"
}
```

**Fall Detection Payload:**
```json
{
    "status": "FALL DOWN",
    "location": {...},
    "IMEI": "865067123456789"
}
```

### AP10 Alarm State Mapping (CORRECTED)

The system correctly identifies alarm types using the `alarm_state` field:

| Alarm State Code | Type | MQTT Topic | Description |
|------------------|------|------------|-------------|
| `'00'` | Normal | None | No alarm - no MQTT message sent |
| `'01'` | SOS | `iMEDE_watch/sos` | SOS emergency button pressed |
| `'03'` | Not Wear | `iMEDE_watch/sos` | Device not worn (default topic) |
| `'05'` | Fall Down | `iMEDE_watch/fallDown` | Fall detection triggered |
| `'06'` | Fall Down | `iMEDE_watch/fallDown` | Fall detection triggered |

**Implementation:**
```python
def _parse_emergency_alarm(self, parsed_packet: Dict[str, Any], imei: str) -> Dict[str, Any]:
    # Use alarm_state info from the packet parser
    alarm_state_info = parsed_packet.get('alarm_state', {})
    alarm_type = alarm_state_info.get('type', 'UNKNOWN')
    
    # Determine status and topic based on alarm state type
    if alarm_type == 'fall_down':
        status = "FALL DOWN"
        topic = f"{self.topic_prefix}/fallDown"
    elif alarm_type == 'SOS':
        status = "SOS"
        topic = f"{self.topic_prefix}/sos"
    else:
        status = alarm_type.upper()
        topic = f"{self.topic_prefix}/sos"  # Default to SOS topic