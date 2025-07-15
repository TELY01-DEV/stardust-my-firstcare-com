#!/usr/bin/env python3
"""
Standalone FHIR Data Validation Module
For use by MQTT listeners without importing the main app module
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class FHIRDataValidator:
    """Standalone FHIR data validation for MQTT listeners"""
    
    @staticmethod
    def validate_kati_data_format(data: Dict[str, Any], topic: str) -> Dict[str, Any]:
        """Validate Kati Watch data format and transform to FHIR-compatible format"""
        errors = []
        warnings = []
        transformed_data = data.copy()
        
        try:
            # Required fields for all Kati messages
            required_fields = ['IMEI']
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
            
            # Topic-specific validation
            if topic == 'iMEDE_watch/VitalSign':
                # Vital signs data
                vital_fields = ['heartRate', 'bloodPressure', 'bodyTemperature', 'spO2']
                for field in vital_fields:
                    if field not in data:
                        warnings.append(f"Missing vital sign field: {field}")
                    else:
                        value = data[field]
                        if field == 'heartRate':
                            if not isinstance(value, (int, float)):
                                errors.append("'heartRate' field must be numeric")
                            elif not (30 <= value <= 250):
                                warnings.append(f"Heart rate {value} outside normal range (30-250 bpm)")
                        elif field == 'bloodPressure':
                            if not isinstance(value, dict):
                                errors.append("'bloodPressure' field must be an object")
                            else:
                                if 'bp_sys' in value:
                                    bp_sys = value['bp_sys']
                                    if not isinstance(bp_sys, (int, float)):
                                        errors.append("'bp_sys' field must be numeric")
                                    elif not (70 <= bp_sys <= 200):
                                        warnings.append(f"Systolic BP {bp_sys} outside normal range")
                                if 'bp_dia' in value:
                                    bp_dia = value['bp_dia']
                                    if not isinstance(bp_dia, (int, float)):
                                        errors.append("'bp_dia' field must be numeric")
                                    elif not (40 <= bp_dia <= 130):
                                        warnings.append(f"Diastolic BP {bp_dia} outside normal range")
                        elif field == 'bodyTemperature':
                            if not isinstance(value, (int, float)):
                                errors.append("'bodyTemperature' field must be numeric")
                            elif not (30 <= value <= 45):
                                warnings.append(f"Temperature {value} outside normal range")
                        elif field == 'spO2':
                            if not isinstance(value, (int, float)):
                                errors.append("'spO2' field must be numeric")
                            elif not (70 <= value <= 100):
                                warnings.append(f"SpO2 {value} outside normal range")
                
                # Optional fields
                if 'battery' in data:
                    battery = data['battery']
                    if not isinstance(battery, (int, float)):
                        errors.append("'battery' field must be numeric")
                    elif not (0 <= battery <= 100):
                        warnings.append("Battery level outside valid range (0-100%)")
                
                # Transform for FHIR
                transformed_data['resource_type'] = 'Observation'
                transformed_data['code'] = 'vital-signs-panel'  # Multiple vital signs
                transformed_data['unit'] = 'mixed'
                transformed_data['category'] = 'vital-signs'
                
            elif topic == 'iMEDE_watch/AP55':
                # Vital signs dataset (hourly upload)
                if 'data' not in data:
                    errors.append("Missing 'data' field for AP55 dataset")
                else:
                    data_list = data['data']
                    if not isinstance(data_list, list):
                        errors.append("'data' field must be an array")
                    else:
                        for i, data_point in enumerate(data_list):
                            if not isinstance(data_point, dict):
                                errors.append(f"Data point {i} must be an object")
                            else:
                                # Validate each data point
                                for field in ['heartRate', 'bloodPressure', 'spO2', 'bodyTemperature']:
                                    if field in data_point:
                                        value = data_point[field]
                                        if field == 'heartRate' and not isinstance(value, (int, float)):
                                            errors.append(f"Data point {i} heartRate must be numeric")
                                        elif field == 'bloodPressure' and not isinstance(value, dict):
                                            errors.append(f"Data point {i} bloodPressure must be an object")
                                        elif field == 'spO2' and not isinstance(value, (int, float)):
                                            errors.append(f"Data point {i} spO2 must be numeric")
                                        elif field == 'bodyTemperature' and not isinstance(value, (int, float)):
                                            errors.append(f"Data point {i} bodyTemperature must be numeric")
                
                # Transform for FHIR
                transformed_data['resource_type'] = 'Observation'
                transformed_data['code'] = 'vital-signs-panel'  # Multiple vital signs
                transformed_data['unit'] = 'mixed'
                transformed_data['category'] = 'vital-signs'
                
            elif topic == 'iMEDE_watch/location':
                # Location data
                if 'location' not in data:
                    errors.append("Missing 'location' field")
                else:
                    location = data['location']
                    if not isinstance(location, dict):
                        errors.append("'location' field must be an object")
                    else:
                        if 'GPS' in location:
                            gps = location['GPS']
                            if not isinstance(gps, dict):
                                errors.append("'GPS' field must be an object")
                            else:
                                for coord in ['latitude', 'longitude']:
                                    if coord in gps:
                                        value = gps[coord]
                                        if not isinstance(value, (int, float)):
                                            errors.append(f"GPS {coord} must be numeric")
                                        elif coord == 'latitude' and not (-90 <= value <= 90):
                                            errors.append("Latitude must be between -90 and 90")
                                        elif coord == 'longitude' and not (-180 <= value <= 180):
                                            errors.append("Longitude must be between -180 and 180")
                
                # Transform for FHIR
                transformed_data['resource_type'] = 'Observation'
                transformed_data['code'] = '86711-2'  # Location LOINC code
                transformed_data['unit'] = 'degrees'
                transformed_data['category'] = 'survey'
                
            elif topic == 'iMEDE_watch/sleepdata':
                # Sleep data
                if 'sleep' not in data:
                    errors.append("Missing 'sleep' field")
                else:
                    sleep = data['sleep']
                    if not isinstance(sleep, dict):
                        errors.append("'sleep' field must be an object")
                    else:
                        if 'data' in sleep:
                            sleep_data = sleep['data']
                            if not isinstance(sleep_data, str):
                                errors.append("Sleep data must be a string")
                
                # Transform for FHIR
                transformed_data['resource_type'] = 'Observation'
                transformed_data['code'] = '93832-4'  # Sleep study LOINC code
                transformed_data['unit'] = 'unknown'
                transformed_data['category'] = 'survey'
                
            elif topic in ['iMEDE_watch/sos', 'iMEDE_watch/fallDown']:
                # Emergency alerts
                if 'status' not in data:
                    errors.append("Missing 'status' field")
                else:
                    status = data['status']
                    if not isinstance(status, str):
                        errors.append("'status' field must be a string")
                    elif status not in ['SOS', 'FALL DOWN']:
                        warnings.append(f"Unknown status: {status}")
                
                # Transform for FHIR
                transformed_data['resource_type'] = 'Observation'
                transformed_data['code'] = 'emergency-alert'
                transformed_data['unit'] = 'unknown'
                transformed_data['category'] = 'survey'
                
            elif topic == 'iMEDE_watch/onlineTrigger':
                # Online/offline status
                if 'status' not in data:
                    errors.append("Missing 'status' field")
                else:
                    status = data['status']
                    if not isinstance(status, str):
                        errors.append("'status' field must be a string")
                    elif status not in ['online', 'offline']:
                        warnings.append(f"Unknown status: {status}")
                
                # Transform for FHIR
                transformed_data['resource_type'] = 'Observation'
                transformed_data['code'] = 'device-status'
                transformed_data['unit'] = 'unknown'
                transformed_data['category'] = 'survey'
                
            else:
                # Unknown topic
                warnings.append(f"Unknown topic: {topic}")
                transformed_data['resource_type'] = 'Observation'
                transformed_data['code'] = 'unknown'
                transformed_data['unit'] = 'unknown'
                transformed_data['category'] = 'unknown'
            
            # Add timestamp if not present
            if 'timestamp' not in transformed_data:
                transformed_data['timestamp'] = datetime.now().isoformat()
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "transformed_data": transformed_data
            }
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "transformed_data": data
            }
    
    @staticmethod
    def validate_ava4_data_format(data: Dict[str, Any], topic: str) -> Dict[str, Any]:
        """Validate AVA4 data format and transform to FHIR-compatible format"""
        errors = []
        warnings = []
        transformed_data = data.copy()
        
        try:
            # Required fields for all AVA4 messages
            required_fields = ['from', 'to', 'time', 'type']
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
            
            if errors:
                return {
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'transformed_data': None
                }
            
            # Validate based on message type
            msg_type = data.get('type')
            
            if msg_type == 'HB_Msg':
                # Heartbeat message - basic validation
                if 'data' not in data or 'msg' not in data.get('data', {}):
                    errors.append("Missing heartbeat message data")
                
            elif msg_type == 'reportMsg':
                # Online trigger message - basic validation
                if 'data' not in data or 'msg' not in data.get('data', {}):
                    errors.append("Missing report message data")
                
            elif msg_type == 'reportAttribute':
                # Vital signs data - comprehensive validation
                if 'data' not in data:
                    errors.append("Missing data field for reportAttribute")
                    return {
                        'valid': False,
                        'errors': errors,
                        'warnings': warnings,
                        'transformed_data': None
                    }
                
                data_section = data['data']
                attribute = data_section.get('attribute', '')
                device = data.get('device', '')
                
                # Validate based on device type
                if attribute == 'BP_BIOLIGTH':  # Blood Pressure
                    value = data_section.get('value', {})
                    if not isinstance(value, dict):
                        errors.append("Blood pressure value must be an object")
                    else:
                        device_list = value.get('device_list', [])
                        if not isinstance(device_list, list) or len(device_list) == 0:
                            errors.append("Blood pressure device_list must be a non-empty array")
                        else:
                            device_data = device_list[0]
                            if 'bp_high' not in device_data or not isinstance(device_data['bp_high'], (int, float)):
                                errors.append("Missing or invalid bp_high (systolic)")
                            if 'bp_low' not in device_data or not isinstance(device_data['bp_low'], (int, float)):
                                errors.append("Missing or invalid bp_low (diastolic)")
                            if 'PR' not in device_data or not isinstance(device_data['PR'], (int, float)):
                                errors.append("Missing or invalid PR (pulse rate)")
                            
                            # Validate ranges
                            if 'bp_high' in device_data and isinstance(device_data['bp_high'], (int, float)):
                                if not (70 <= device_data['bp_high'] <= 250):
                                    warnings.append(f"Systolic pressure {device_data['bp_high']} may be outside normal range")
                            if 'bp_low' in device_data and isinstance(device_data['bp_low'], (int, float)):
                                if not (40 <= device_data['bp_low'] <= 150):
                                    warnings.append(f"Diastolic pressure {device_data['bp_low']} may be outside normal range")
                            if 'PR' in device_data and isinstance(device_data['PR'], (int, float)):
                                if not (40 <= device_data['PR'] <= 200):
                                    warnings.append(f"Pulse rate {device_data['PR']} may be outside normal range")
                
                elif attribute == 'Oximeter JUMPER':  # SpO2
                    value = data_section.get('value', {})
                    if not isinstance(value, dict):
                        errors.append("SpO2 value must be an object")
                    else:
                        device_list = value.get('device_list', [])
                        if not isinstance(device_list, list) or len(device_list) == 0:
                            errors.append("SpO2 device_list must be a non-empty array")
                        else:
                            device_data = device_list[0]
                            if 'spo2' not in device_data or not isinstance(device_data['spo2'], (int, float)):
                                errors.append("Missing or invalid spo2")
                            if 'pulse' not in device_data or not isinstance(device_data['pulse'], (int, float)):
                                errors.append("Missing or invalid pulse rate")
                            if 'pi' not in device_data or not isinstance(device_data['pi'], (int, float)):
                                warnings.append("Missing or invalid perfusion index")
                            
                            # Validate ranges
                            if 'spo2' in device_data and isinstance(device_data['spo2'], (int, float)):
                                if not (70 <= device_data['spo2'] <= 100):
                                    warnings.append(f"SpO2 {device_data['spo2']} may be outside normal range")
                            if 'pulse' in device_data and isinstance(device_data['pulse'], (int, float)):
                                if not (40 <= device_data['pulse'] <= 200):
                                    warnings.append(f"Pulse rate {device_data['pulse']} may be outside normal range")
                
                elif attribute in ['Contour_Elite', 'AccuChek_Instant']:  # Blood Glucose
                    value = data_section.get('value', {})
                    if not isinstance(value, dict):
                        errors.append("Blood glucose value must be an object")
                    else:
                        device_list = value.get('device_list', [])
                        if not isinstance(device_list, list) or len(device_list) == 0:
                            errors.append("Blood glucose device_list must be a non-empty array")
                        else:
                            device_data = device_list[0]
                            if 'blood_glucose' not in device_data:
                                errors.append("Missing blood_glucose")
                            else:
                                # Handle string or numeric blood glucose values
                                bg_value = device_data['blood_glucose']
                                if isinstance(bg_value, str):
                                    try:
                                        bg_value = float(bg_value)
                                    except ValueError:
                                        errors.append("Invalid blood_glucose value (cannot convert to number)")
                                elif not isinstance(bg_value, (int, float)):
                                    errors.append("Blood glucose must be numeric")
                                
                                if isinstance(bg_value, (int, float)) and not (20 <= bg_value <= 600):
                                    warnings.append(f"Blood glucose {bg_value} may be outside normal range")
                            
                            if 'marker' not in device_data:
                                warnings.append("Missing meal marker (Before Meal/After Meal)")
                
                elif attribute == 'IR_TEMO_JUMPER':  # Body Temperature
                    value = data_section.get('value', {})
                    if not isinstance(value, dict):
                        errors.append("Temperature value must be an object")
                    else:
                        device_list = value.get('device_list', [])
                        if not isinstance(device_list, list) or len(device_list) == 0:
                            errors.append("Temperature device_list must be a non-empty array")
                        else:
                            device_data = device_list[0]
                            if 'temp' not in device_data or not isinstance(device_data['temp'], (int, float)):
                                errors.append("Missing or invalid temperature")
                            if 'mode' not in device_data:
                                warnings.append("Missing temperature measurement mode")
                            
                            # Validate ranges
                            if 'temp' in device_data and isinstance(device_data['temp'], (int, float)):
                                if not (30 <= device_data['temp'] <= 45):
                                    warnings.append(f"Temperature {device_data['temp']} may be outside normal range")
                
                elif attribute == 'BodyScale_JUMPER':  # Weight Scale
                    value = data_section.get('value', {})
                    if not isinstance(value, dict):
                        errors.append("Weight scale value must be an object")
                    else:
                        device_list = value.get('device_list', [])
                        if not isinstance(device_list, list) or len(device_list) == 0:
                            errors.append("Weight scale device_list must be a non-empty array")
                        else:
                            device_data = device_list[0]
                            if 'weight' not in device_data or not isinstance(device_data['weight'], (int, float)):
                                errors.append("Missing or invalid weight")
                            if 'resistance' not in device_data or not isinstance(device_data['resistance'], (int, float)):
                                warnings.append("Missing or invalid body resistance")
                            
                            # Validate ranges
                            if 'weight' in device_data and isinstance(device_data['weight'], (int, float)):
                                if not (10 <= device_data['weight'] <= 300):
                                    warnings.append(f"Weight {device_data['weight']} may be outside normal range")
                
                elif attribute == 'MGSS_REF_UA':  # Uric Acid
                    value = data_section.get('value', {})
                    if not isinstance(value, dict):
                        errors.append("Uric acid value must be an object")
                    else:
                        device_list = value.get('device_list', [])
                        if not isinstance(device_list, list) or len(device_list) == 0:
                            errors.append("Uric acid device_list must be a non-empty array")
                        else:
                            device_data = device_list[0]
                            if 'uric_acid' not in device_data:
                                errors.append("Missing uric_acid")
                            else:
                                # Handle string or numeric uric acid values
                                ua_value = device_data['uric_acid']
                                if isinstance(ua_value, str):
                                    try:
                                        ua_value = float(ua_value)
                                    except ValueError:
                                        errors.append("Invalid uric_acid value (cannot convert to number)")
                                elif not isinstance(ua_value, (int, float)):
                                    errors.append("Uric acid must be numeric")
                                
                                if isinstance(ua_value, (int, float)) and not (1 <= ua_value <= 1000):
                                    warnings.append(f"Uric acid {ua_value} may be outside normal range")
                
                elif attribute == 'MGSS_REF_CHOL':  # Cholesterol
                    value = data_section.get('value', {})
                    if not isinstance(value, dict):
                        errors.append("Cholesterol value must be an object")
                    else:
                        device_list = value.get('device_list', [])
                        if not isinstance(device_list, list) or len(device_list) == 0:
                            errors.append("Cholesterol device_list must be a non-empty array")
                        else:
                            device_data = device_list[0]
                            if 'cholesterol' not in device_data:
                                errors.append("Missing cholesterol")
                            else:
                                # Handle string or numeric cholesterol values
                                chol_value = device_data['cholesterol']
                                if isinstance(chol_value, str):
                                    try:
                                        chol_value = float(chol_value)
                                    except ValueError:
                                        errors.append("Invalid cholesterol value (cannot convert to number)")
                                elif not isinstance(chol_value, (int, float)):
                                    errors.append("Cholesterol must be numeric")
                                
                                if isinstance(chol_value, (int, float)) and not (1 <= chol_value <= 20):
                                    warnings.append(f"Cholesterol {chol_value} may be outside normal range")
                
                else:
                    warnings.append(f"Unknown device attribute: {attribute}")
            
            else:
                warnings.append(f"Unknown message type: {msg_type}")
            
            # Add device information
            if 'deviceCode' in data:
                transformed_data['device_code'] = data['deviceCode']
            if 'mac' in data:
                transformed_data['device_mac'] = data['mac']
            if 'IMEI' in data:
                transformed_data['device_imei'] = data['IMEI']
            if 'name' in data:
                transformed_data['device_name'] = data['name']
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'transformed_data': transformed_data if len(errors) == 0 else None
            }
            
        except Exception as e:
            logger.error(f"Error in AVA4 data validation: {str(e)}")
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': warnings,
                'transformed_data': None
            }
    
    @staticmethod
    def validate_qube_data_format(data: Dict[str, Any], topic: str) -> Dict[str, Any]:
        """Validate Qube-Vital data format and transform to FHIR-compatible format"""
        errors = []
        warnings = []
        transformed_data = data.copy()
        
        try:
            # Required fields for all Qube messages
            required_fields = ['from', 'to', 'time', 'mac', 'type']
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
            
            if errors:
                return {
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'transformed_data': None
                }
            
            # Validate based on message type
            msg_type = data.get('type')
            
            if msg_type == 'HB_Msg':
                # Heartbeat message - basic validation
                if 'data' not in data or 'msg' not in data.get('data', {}):
                    errors.append("Missing heartbeat message data")
                
            elif msg_type == 'reportAttribute':
                # Vital signs data - comprehensive validation
                if 'data' not in data:
                    errors.append("Missing data field for reportAttribute")
                    return {
                        'valid': False,
                        'errors': errors,
                        'warnings': warnings,
                        'transformed_data': None
                    }
                
                data_section = data['data']
                attribute = data_section.get('attribute', '')
                
                # Validate based on device type
                if attribute == 'WBP_JUMPER':  # Blood Pressure
                    value = data_section.get('value', {})
                    if not isinstance(value, dict):
                        errors.append("Blood pressure value must be an object")
                    else:
                        if 'bp_high' not in value or not isinstance(value['bp_high'], (int, float)):
                            errors.append("Missing or invalid bp_high (systolic)")
                        if 'bp_low' not in value or not isinstance(value['bp_low'], (int, float)):
                            errors.append("Missing or invalid bp_low (diastolic)")
                        if 'pr' not in value or not isinstance(value['pr'], (int, float)):
                            errors.append("Missing or invalid pr (pulse rate)")
                        
                        # Validate ranges
                        if 'bp_high' in value and isinstance(value['bp_high'], (int, float)):
                            if not (70 <= value['bp_high'] <= 250):
                                warnings.append(f"Systolic pressure {value['bp_high']} may be outside normal range")
                        if 'bp_low' in value and isinstance(value['bp_low'], (int, float)):
                            if not (40 <= value['bp_low'] <= 150):
                                warnings.append(f"Diastolic pressure {value['bp_low']} may be outside normal range")
                        if 'pr' in value and isinstance(value['pr'], (int, float)):
                            if not (40 <= value['pr'] <= 200):
                                warnings.append(f"Pulse rate {value['pr']} may be outside normal range")
                
                elif attribute == 'CONTOUR':  # Blood Glucose
                    value = data_section.get('value', {})
                    if not isinstance(value, dict):
                        errors.append("Blood glucose value must be an object")
                    else:
                        if 'blood_glucose' not in value or not isinstance(value['blood_glucose'], (int, float)):
                            errors.append("Missing or invalid blood_glucose")
                        if 'marker' not in value:
                            warnings.append("Missing meal marker (Before Meal/After Meal)")
                        
                        # Validate ranges
                        if 'blood_glucose' in value and isinstance(value['blood_glucose'], (int, float)):
                            if not (20 <= value['blood_glucose'] <= 600):
                                warnings.append(f"Blood glucose {value['blood_glucose']} may be outside normal range")
                
                elif attribute == 'BodyScale_JUMPER':  # Weight Scale
                    value = data_section.get('value', {})
                    if not isinstance(value, dict):
                        errors.append("Weight scale value must be an object")
                    else:
                        if 'weight' not in value or not isinstance(value['weight'], (int, float)):
                            errors.append("Missing or invalid weight")
                        if 'Resistance' not in value or not isinstance(value['Resistance'], (int, float)):
                            warnings.append("Missing or invalid body resistance")
                        
                        # Validate ranges
                        if 'weight' in value and isinstance(value['weight'], (int, float)):
                            if not (10 <= value['weight'] <= 300):
                                warnings.append(f"Weight {value['weight']} may be outside normal range")
                
                elif attribute == 'TEMO_Jumper':  # Body Temperature
                    value = data_section.get('value', {})
                    if not isinstance(value, dict):
                        errors.append("Temperature value must be an object")
                    else:
                        if 'Temp' not in value or not isinstance(value['Temp'], (int, float)):
                            errors.append("Missing or invalid temperature")
                        if 'mode' not in value:
                            warnings.append("Missing temperature measurement mode")
                        
                        # Validate ranges
                        if 'Temp' in value and isinstance(value['Temp'], (int, float)):
                            if not (30 <= value['Temp'] <= 45):
                                warnings.append(f"Temperature {value['Temp']} may be outside normal range")
                
                elif attribute == 'Oximeter_JUMPER':  # SpO2
                    value = data_section.get('value', {})
                    if not isinstance(value, dict):
                        errors.append("SpO2 value must be an object")
                    else:
                        if 'spo2' not in value or not isinstance(value['spo2'], (int, float)):
                            errors.append("Missing or invalid SpO2")
                        if 'pulse' not in value or not isinstance(value['pulse'], (int, float)):
                            errors.append("Missing or invalid pulse rate")
                        if 'pi' not in value or not isinstance(value['pi'], (int, float)):
                            warnings.append("Missing or invalid perfusion index")
                        
                        # Validate ranges
                        if 'spo2' in value and isinstance(value['spo2'], (int, float)):
                            if not (70 <= value['spo2'] <= 100):
                                warnings.append(f"SpO2 {value['spo2']} may be outside normal range")
                        if 'pulse' in value and isinstance(value['pulse'], (int, float)):
                            if not (40 <= value['pulse'] <= 200):
                                warnings.append(f"Pulse rate {value['pulse']} may be outside normal range")
                
                else:
                    warnings.append(f"Unknown device attribute: {attribute}")
            
            else:
                warnings.append(f"Unknown message type: {msg_type}")
            
            # Add patient information if available
            if 'citiz' in data:
                transformed_data['patient_id'] = data['citiz']
            if 'nameTH' in data:
                transformed_data['patient_name_th'] = data['nameTH']
            if 'nameEN' in data:
                transformed_data['patient_name_en'] = data['nameEN']
            if 'brith' in data:
                transformed_data['patient_birth'] = data['brith']
            if 'gender' in data:
                transformed_data['patient_gender'] = data['gender']
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'transformed_data': transformed_data if len(errors) == 0 else None
            }
            
        except Exception as e:
            logger.error(f"Error in Qube-Vital data validation: {str(e)}")
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': warnings,
                'transformed_data': None
            }

# Create a singleton instance
fhir_validator = FHIRDataValidator() 