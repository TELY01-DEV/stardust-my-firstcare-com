What's your MQTT broker URL and credentials?
# MQTT Configuration (External)
MQTT_ENABLED=true
MQTT_BROKER_HOST=adam.amy.care
MQTT_BROKER_PORT=1883
MQTT_USERNAME=webapi
MQTT_PASSWORD=Sim!4433
MQTT_QOS=1
MQTT_RETAIN=false
MQTT_KEEPALIVE=60
MQTT_CONNECTION_TIMEOUT=10

2. Device-Patient Mapping
How do you currently map devices to patients? Check below i have mention the collection.document field

For AVA4: Is it via mac_address in amy_boxes → patient_id ?
- amy_boxes.mac_address -> patients.ava_mac_address

For Medical Devices 
amy_devices.patient_id -> patients._id

- Blood Pressure 
amy_devices.mac_dusun_bps -> patients.blood_pressure_mac_address
- SpO2
amy_devices.mac_oxymeter -> patients.fingertip_pulse_oximeter_mac_address
- Body Temp
amy_devices.mac_body_temp -> patients.body_temperature_mac_address
- Body Weight scale
amy_devices.mac_weight -> patients.weight_scale_mac_address
- Blood Sugar(DTX)
amy_devices.mac_gluc -> patients.blood_glucose_mac_address
- Uric
amy_devices.mac_ua -> patients.uric_mac_address
- Cholesterol
amy_devices.mac_chol -> patients.cholesterol_mac_address

For Kati: Is it via IMEI in watches?
- watches.imei -> patients.watch_mac_address

For Qube-Vital: Is it via citiz field directly?
- mfc_hv01_boxes.imei_of_hv01_box -> hospitals.mac_hv01_box
Medical Data from Qube-Vital (MQTT Topic: CM4_BLE_GW_TX)
step of processing data
1. look up from patient collection for existing CID
2. if it not have we need to create new patient with data from payload and mark as unrisgtered patient status
3. if CID existing need to store the medical data to patient collection and all medical history

## 📊 **MQTT Configuration & Device Mapping Summary**

### **MQTT Broker Details:**
- **Host**: `adam.amy.care:1883`
- **Credentials**: `webapi` / `Sim!4433`
- **QoS**: 1
- **Keepalive**: 60 seconds

### **Device-Patient Mapping Logic:**

#### **AVA4 + Sub-devices:**
```
1. AVA4 Box: amy_boxes.mac_address → patients.ava_mac_address
2. Medical Devices: amy_devices.patient_id → patients._id
3. Device-Specific MAC Mapping:
   - Blood Pressure: amy_devices.mac_dusun_bps → patients.blood_pressure_mac_address
   - SpO2: amy_devices.mac_oxymeter → patients.fingertip_pulse_oximeter_mac_address
   - Body Temp: amy_devices.mac_body_temp → patients.body_temperature_mac_address
   - Weight Scale: amy_devices.mac_weight → patients.weight_scale_mac_address
   - Blood Sugar: amy_devices.mac_gluc → patients.blood_glucose_mac_address
   - Uric Acid: amy_devices.mac_ua → patients.uric_mac_address
   - Cholesterol: amy_devices.mac_chol → patients.cholesterol_mac_address
```

#### **Kati Watch:**
```
watches.imei → patients.watch_mac_address
```

#### **Qube-Vital:**
```
1. Device Mapping: mfc_hv01_boxes.imei_of_hv01_box → hospitals.mac_hv01_box
2. Patient Lookup: payload.citiz → patients.id_card
3. Auto-create patient if CID not found (unregistered status)
```

## 🏗️ **Implementation Plan**

### **Phase 1: MQTT Listener Services Structure**

Let me create the Docker Compose configuration and service structure: