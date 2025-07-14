
# 📡 AVA4 MQTT Topics & Payload Examples (with Explanation)

> **⚠️ Important Note:** While the examples below show `dusun_pub` as the topic for BLE medical device data, the actual application is configured to use `dusun_sub` for subdevice payload. The payload structure remains the same, only the topic name differs.

---

## 🔹 1. Heartbeat Message (AVA4 Device Status)

**Topic:** `ESP32_BLE_GW_TX`  
**Payload:**
```json
{
  "from": "ESP32_GW",
  "to": "CLOUD",
  "name": "AVA4-No.1",
  "time": 1743963911,
  "mac": "DC:DA:0C:5A:80:64",
  "IMEI": "868334037510868",
  "ICCID": "8966032240112716129",
  "type": "HB_Msg",
  "data": {
    "msg": "Online"
  }
}


## 🔹 2. Online Trigger Message

**Topic:** `ESP32_BLE_GW_TX`  
**Payload:**
```json
{
  "from": "ESP32_S3_GW",
  "to": "CLOUD",
  "time": 1743932465,
  "mac": "DC:DA:0C:5A:FF:FF",
  "IMEI": "868334037510868",
  "ICCID": "8966032240112716129",
  "type": "reportMsg",
  "data": {
    "msg": "Online"
  }
}
```

**📘 Explanation:**
- Sent **once** when AVA4 powers on
- Used to detect "Back Online" or "First Online"
- May trigger alert or status change log

---

## 🔹 3. Medical Device Data Report (Subdevice)

**Topic:** `dusun_pub`  
**Payload:**
```json
{
  "from": "BLE",
  "to": "CLOUD",
  "time": 1836942771,
  "deviceCode": "08:F9:E0:D1:F7:B4",
  "mac": "08:F9:E0:D1:F7:B4",
  "type": "reportAttribute",
  "device": "WBP BIOLIGHT",
  "data": {
    "attribute": "BP_BIOLIGTH",
    "mac": "08:F9:E0:D1:F7:B4",
    "value": {
      "device_list": [
        {
          "scan_time": 1836942771,
          "ble_addr": "d616f9641622",
          "bp_high": 137,
          "bp_low": 95,
          "PR": 74
        }
      ]
    }
  }
}
```

**📘 Explanation:**
- Medical reading sent from BLE subdevice via AVA4
- Identified by `ble_addr` and `attribute`
- Parsed and converted into FHIR `Observation`
- Related to AVA4 `IMEI`/`mac` (used in device provenance)

---

## 🔹 4. Oximeter Report (Another Subdevice Type)

**Topic:** `dusun_pub`  
**Payload:**
```json
{
  "from": "BLE",
  "to": "CLOUD",
  "time": 1836946958,
  "deviceCode": "DC:DA:0C:5A:80:44",
  "mac": "DC:DA:0C:5A:80:44",
  "type": "reportAttribute",
  "device": "Oximeter Jumper",
  "data": {
    "attribute": "Oximeter JUMPER",
    "mac": "DC:DA:0C:5A:80:44",
    "value": {
      "device_list": [
        {
          "scan_time": 1836946958,
          "ble_addr": "ff23041920b4",
          "pulse": 72,
          "spo2": 96,
          "pi": 43
        }
      ]
    }
  }
}
```

## 🔹 5. Glucometer - Contour Elite

**Topic:** `dusun_pub`  
**Payload:**
```json
{
  "from": "BLE",
  "to": "CLOUD",
  "time": 1841875953,
  "deviceCode": "DC:DA:0C:5A:80:88",
  "mac": "DC:DA:0C:5A:80:88",
  "type": "reportAttribute",
  "device": "SUGA Contour",
  "data": {
    "attribute": "Contour_Elite",
    "mac": "DC:DA:0C:5A:80:88",
    "value": {
      "device_list": [{
        "scan_time": 1841875953,
        "ble_addr": "806fb0750c88",
        "scan_rssi": -66,
        "blood_glucose": "108",
        "marker": "After Meal"
      }]
    }
  }
}
```

---

## 🔹 6. Glucometer - AccuChek Instant

**Topic:** `dusun_pub`  
**Payload:**
```json
{
  "from": "BLE",
  "to": "CLOUD",
  "time": 1841875953,
  "deviceCode": "80:65:99:A1:DC:77",
  "mac": "80:65:99:A1:DC:77",
  "type": "reportAttribute",
  "device": "SUGA AccuCheck",
  "data": {
    "attribute": "AccuChek_Instant",
    "mac": "80:65:99:A1:DC:77",
    "value": {
      "device_list": [{
        "scan_time": 1841875953,
        "ble_addr": "60e85b7aab77",
        "scan_rssi": -66,
        "blood_glucose": "111",
        "marker": "After Meal"
      }]
    }
  }
}
```

---

## 🔹 7. Thermometer - Jumper IR

**Topic:** `dusun_pub`  
**Payload:**
```json
{
  "from": "BLE",
  "to": "CLOUD",
  "time": 1841932446,
  "deviceCode": "DC:DA:0C:5A:80:64",
  "mac": "DC:DA:0C:5A:80:64",
  "type": "reportAttribute",
  "device": "TEMO Jumper",
  "data": {
    "attribute": "IR_TEMO_JUMPER",
    "mac": "DC:DA:0C:5A:80:64",
    "value": {
      "device_list": [{
        "scan_time": 1841932446,
        "ble_addr": "ff2301283119",
        "temp": 36.43000031,
        "mode": "Head"
      }]
    }
  }
}
```

---

## 🔹 8. Weight Scale - Jumper

**Topic:** `dusun_pub`  
**Payload:**
```json
{
  "from": "BLE",
  "to": "CLOUD",
  "time": 1773337306,
  "deviceCode": "DC:DA:0C:5A:80:33",
  "mac": "DC:DA:0C:5A:80:33",
  "type": "reportAttribute",
  "device": "JUMPER SCALE",
  "data": {
    "attribute": "BodyScale_JUMPER",
    "mac": "DC:DA:0C:5A:80:33",
    "value": {
      "device_list": [{
        "scan_time": 1773337306,
        "ble_addr": "A0779E1C14D8",
        "weight": 79.30000305,
        "resistance": 605.9000244
      }]
    }
  }
}
```

---

## 🔹 9. Uric Acid - MGSS_REF_UA

**Topic:** `dusun_pub`  
**Payload:**
```json
{
  "from": "BLE",
  "to": "CLOUD",
  "time": 1841875953,
  "deviceCode": "34:20:03:9a:13:22",
  "mac": "34:20:03:9a:13:22",
  "type": "reportAttribute",
  "device": "Uric REF_UA",
  "data": {
    "attribute": "MGSS_REF_UA",
    "mac": "34:20:03:9a:13:22",
    "value": {
      "device_list": [{
        "scan_time": 1841875953,
        "ble_addr": "60e85b7aab77",
        "scan_rssi": -66,
        "uric_acid": "517.5"
      }]
    }
  }
}
```

---

## 🔹 10. Cholesterol - MGSS_REF_CHOL

**Topic:** `dusun_pub`  
**Payload:**
```json
{
  "from": "BLE",
  "to": "CLOUD",
  "time": 1841875953,
  "deviceCode": "34:20:03:9a:13:11",
  "mac": "34:20:03:9a:13:11",
  "type": "reportAttribute",
  "device": "Cholesterol REF_CHOL",
  "data": {
    "attribute": "MGSS_REF_CHOL",
    "mac": "34:20:03:9a:13:11",
    "value": {
      "device_list": [{
        "scan_time": 1841875953,
        "ble_addr": "0035FF226907",
        "scan_rssi": -66,
        "cholesterol": "4.3"
      }]
    }
  }
}
```

