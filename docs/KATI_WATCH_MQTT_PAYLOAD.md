#### 1. Heartbeat come with step data
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

#### 2. Single Vital Signs Data
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

#### 3. Vital Sign Dataset
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

#### 4. Location
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

#### 5. Sleep Data
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

#### 6. Emergency Alarm 
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

**Topic:** `iMEDE_watch/onlineTrigger`

**Payload:**
```json
{
    "IMEI": "865067123456789",
    "status": "online"  // or "offline"
}
```