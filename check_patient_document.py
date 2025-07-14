#!/usr/bin/env python3
"""
Script to check raw patient document structure for health/medical data storage
Using production API endpoint
"""

import asyncio
import aiohttp
import json
from datetime import datetime

# API Configuration
API_BASE_URL = "https://stardust.my-firstcare.com"
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2NjY2NjY2NjY2NjY2IiwidXNlcl9pZCI6IjY2NjY2NjY2NjY2NjYiLCJlbWFpbCI6ImFkbWluQGV4YW1wbGUuY29tIiwicm9sZSI6ImFkbWluIiwiaWF0IjoxNzM0NzE5NzE5LCJleHAiOjE3MzQ4MDUxMTl9.8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q8Q"

async def check_patient_document(patient_id: str):
    """Check raw patient document structure for health/medical data fields"""
    
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Get raw patient documents with specific patient ID
            url = f"{API_BASE_URL}/admin/patients-raw-documents"
            params = {
                "patient_id": patient_id,
                "limit": 1,
                "skip": 0
            }
            
            print(f"🔍 Fetching patient document from: {url}")
            print(f"📋 Patient ID: {patient_id}")
            print("=" * 80)
            
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("success") and data.get("data", {}).get("raw_documents"):
                        patient_doc = data["data"]["raw_documents"][0]
                        field_analysis = data["data"].get("field_analysis", {})
                        
                        print(f"✅ Found patient document")
                        print(f"📊 Total fields: {len(patient_doc)}")
                        print("=" * 80)
                        
                        # Analyze document structure
                        print("📊 PATIENT DOCUMENT STRUCTURE ANALYSIS")
                        print("=" * 80)
                        
                        # Categorize fields
                        categories = {
                            "Basic Information": [
                                "first_name", "last_name", "nickname", "gender", "birth_date",
                                "id_card", "phone", "email"
                            ],
                            "Address Information": [
                                "address", "province_code", "district_code", "sub_district_code", "postal_code"
                            ],
                            "Emergency Contact": [
                                "emergency_contact_name", "emergency_contact_phone", "emergency_contact_relationship"
                            ],
                            "Medical Information": [
                                "blood_type", "height", "weight", "bmi"
                            ],
                            "Device Mappings": [
                                "watch_mac_address", "ava_mac_address", "new_hospital_ids"
                            ],
                            "Medical Device MAC Addresses": [
                                "blood_pressure_mac_address", "blood_glucose_mac_address",
                                "body_temperature_mac_address", "fingertip_pulse_oximeter_mac_address",
                                "cholesterol_mac_address"
                            ],
                            "Medical Alert Thresholds": [
                                "bp_sbp_above", "bp_sbp_below", "bp_dbp_above", "bp_dbp_below",
                                "glucose_normal_before", "glucose_normal_after",
                                "temperature_normal_above", "temperature_normal_below",
                                "spo2_normal_above", "spo2_normal_below",
                                "cholesterol_above", "cholesterol_below"
                            ],
                            "Medical History Fields": [
                                "blood_preassure_import_date", "blood_sugar_import_date",
                                "cretinines_import_date", "cholesterol_import_date",
                                "blood_preassure_source", "blood_sugar_source",
                                "blood_sugar_symptoms", "blood_sugar_other_symptoms",
                                "bmi", "cholesterol", "bun", "creatinine"
                            ],
                            "Status & Audit": [
                                "is_active", "is_deleted", "created_at", "updated_at",
                                "unique_id", "__v"
                            ]
                        }
                        
                        # Analyze each category
                        for category, fields in categories.items():
                            print(f"\n🔍 {category.upper()}")
                            print("-" * 40)
                            
                            category_fields = {}
                            for field in fields:
                                if field in patient_doc:
                                    value = patient_doc[field]
                                    # Get data type from field analysis if available
                                    data_type = field_analysis.get(field, {}).get("data_types", ["unknown"])[0] if field in field_analysis else "unknown"
                                    category_fields[field] = {
                                        "value": value,
                                        "type": data_type,
                                        "exists": True
                                    }
                                else:
                                    category_fields[field] = {
                                        "value": None,
                                        "type": "missing",
                                        "exists": False
                                    }
                            
                            # Display fields in this category
                            for field, info in category_fields.items():
                                if info["exists"]:
                                    value_str = str(info["value"])[:50] + "..." if len(str(info["value"])) > 50 else str(info["value"])
                                    print(f"  ✅ {field}: {value_str} ({info['type']})")
                                else:
                                    print(f"  ❌ {field}: Not present")
                        
                        # Check for additional health/medical fields not in standard categories
                        print(f"\n🔍 ADDITIONAL HEALTH/MEDICAL FIELDS")
                        print("-" * 40)
                        
                        all_standard_fields = []
                        for fields in categories.values():
                            all_standard_fields.extend(fields)
                        
                        additional_medical_fields = []
                        for field, value in patient_doc.items():
                            if field not in all_standard_fields:
                                # Check if it looks like medical/health data
                                medical_keywords = [
                                    "blood", "pressure", "sugar", "glucose", "temperature", "spo2",
                                    "cholesterol", "creatinine", "bun", "weight", "height", "bmi",
                                    "allergy", "medication", "disease", "symptom", "threshold",
                                    "alert", "normal", "above", "below", "import", "source"
                                ]
                                
                                if any(keyword in field.lower() for keyword in medical_keywords):
                                    data_type = field_analysis.get(field, {}).get("data_types", ["unknown"])[0] if field in field_analysis else "unknown"
                                    additional_medical_fields.append((field, value, data_type))
                        
                        if additional_medical_fields:
                            for field, value, data_type in additional_medical_fields:
                                value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                                print(f"  📊 {field}: {value_str} ({data_type})")
                        else:
                            print("  ℹ️  No additional medical fields found")
                        
                        # Summary
                        print(f"\n📈 DOCUMENT SUMMARY")
                        print("=" * 80)
                        print(f"Total fields in document: {len(patient_doc)}")
                        print(f"Standard fields present: {sum(1 for field in all_standard_fields if field in patient_doc)}")
                        print(f"Additional medical fields: {len(additional_medical_fields)}")
                        
                        # Show field analysis from API
                        if field_analysis:
                            print(f"\n📊 FIELD ANALYSIS FROM API")
                            print("-" * 40)
                            for field, analysis in list(field_analysis.items())[:10]:  # Show first 10 fields
                                data_types = ", ".join(analysis.get("data_types", []))
                                sample_values = analysis.get("sample_values", [])
                                sample_str = ", ".join([str(v)[:20] for v in sample_values[:2]]) if sample_values else "None"
                                print(f"  📋 {field}: {data_types} | Samples: {sample_str}")
                        
                        # Recommendations for health data storage
                        print(f"\n💡 RECOMMENDATIONS FOR HEALTH DATA STORAGE")
                        print("=" * 80)
                        print("Based on the patient document structure, health/medical data should be stored in:")
                        print()
                        print("1. 📋 PATIENT DOCUMENT FIELDS (Direct storage):")
                        print("   - Medical alert thresholds (bp_sbp_above, glucose_normal_before, etc.)")
                        print("   - Basic medical info (blood_type, height, weight, bmi)")
                        print("   - Device mappings (watch_mac_address, ava_mac_address)")
                        print("   - Import dates and sources for medical data")
                        print()
                        print("2. 📊 MEDICAL HISTORY COLLECTIONS (Structured storage):")
                        print("   - blood_pressure_histories")
                        print("   - blood_sugar_histories") 
                        print("   - body_data_histories")
                        print("   - creatinine_histories")
                        print("   - lipid_histories")
                        print("   - sleep_data_histories")
                        print("   - spo2_histories")
                        print("   - step_histories")
                        print("   - temperature_data_histories")
                        print("   - allergy_histories")
                        print("   - underlying_disease_histories")
                        print("   - admit_data_histories")
                        print()
                        print("3. 🔗 DEVICE-PATIENT MAPPING:")
                        print("   - AVA4: Use ava_mac_address field")
                        print("   - Kati Watch: Use watch_mac_address field")
                        print("   - Qube-Vital: Use citizen_id and hospital MAC mapping")
                        print()
                        print("4. 📝 TRANSACTION LOGGING:")
                        print("   - Store real-time processing events in transaction_logs collection")
                        print("   - Include device_id, patient_id, data_type, timestamp")
                        print("   - Link to medical history collections for detailed data")
                        
                    else:
                        print("❌ No patient documents found in response")
                        print(f"Response: {json.dumps(data, indent=2)}")
                        
                else:
                    print(f"❌ API request failed with status {response.status}")
                    error_text = await response.text()
                    print(f"Error response: {error_text}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")

async def main():
    """Main function"""
    patient_id = "623c133cf9e69c3b67a9af64"
    print(f"🔍 Checking patient document structure for ID: {patient_id}")
    print(f"🌐 Using API endpoint: {API_BASE_URL}")
    print("=" * 80)
    
    await check_patient_document(patient_id)

if __name__ == "__main__":
    asyncio.run(main()) 