from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from .base import BaseDocument, PyObjectId

# Medical History Base Models
class MedicalHistoryBase(BaseModel):
    patient_id: str = Field(..., description="Patient ID reference")
    device_id: Optional[str] = Field(None, description="Device ID that recorded the data")
    device_type: Optional[str] = Field(None, description="Type of device (AVA4, Kati, Qube-Vital)")
    timestamp: Optional[datetime] = Field(None, description="When the measurement was taken")
    notes: Optional[str] = Field(None, description="Additional notes")

class MedicalHistoryCreate(MedicalHistoryBase):
    history_type: str = Field(..., description="Type of medical history (blood_pressure, blood_sugar, etc.)")
    values: Dict[str, Any] = Field(..., description="Medical data values specific to history type")

class MedicalHistoryUpdate(BaseModel):
    device_id: Optional[str] = None
    device_type: Optional[str] = None
    timestamp: Optional[datetime] = None
    values: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class MedicalHistory(BaseDocument):
    patient_id: PyObjectId = Field(...)
    device_id: Optional[str] = None
    device_type: Optional[str] = None
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Array of medical data entries")
    timestamp: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            PyObjectId: lambda v: str(v)
        }

class MedicalHistoryResponse(BaseModel):
    id: str = Field(alias="_id")
    patient_id: str
    device_id: Optional[str] = None
    device_type: Optional[str] = None
    data: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Search and Filter Models
class MedicalHistorySearchQuery(BaseModel):
    search: Optional[str] = Field(None, description="General search across data fields")
    patient_id: Optional[str] = Field(None, description="Filter by patient ID")
    device_id: Optional[str] = Field(None, description="Filter by device ID")
    device_type: Optional[str] = Field(None, description="Filter by device type")
    date_from: Optional[datetime] = Field(None, description="Start date filter")
    date_to: Optional[datetime] = Field(None, description="End date filter")
    value_min: Optional[float] = Field(None, description="Minimum value filter (for numeric data)")
    value_max: Optional[float] = Field(None, description="Maximum value filter (for numeric data)")

# Statistics Models
class MedicalHistoryStats(BaseModel):
    total_records: int = Field(..., description="Total number of medical history records")
    records_by_type: List[Dict[str, Any]] = Field(..., description="Record counts by history type")
    records_by_patient: List[Dict[str, Any]] = Field(..., description="Record counts by patient")
    records_by_device: List[Dict[str, Any]] = Field(..., description="Record counts by device")
    date_range: Dict[str, Any] = Field(..., description="Date range of records")

# Bulk Operations Models
class BulkMedicalHistoryDelete(BaseModel):
    record_ids: List[str] = Field(..., description="List of record IDs to delete")
    history_type: str = Field(..., description="Type of medical history")

class BulkMedicalHistoryUpdate(BaseModel):
    record_ids: List[str] = Field(..., description="List of record IDs to update")
    history_type: str = Field(..., description="Type of medical history")
    update_data: Dict[str, Any] = Field(..., description="Data to update")

# Collection Info Model
class MedicalHistoryCollectionInfo(BaseModel):
    collection_name: str = Field(..., description="MongoDB collection name")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Collection description")
    record_count: int = Field(..., description="Number of records")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    data_fields: List[str] = Field(..., description="Available data fields")
    status: str = Field(..., description="Collection status")

class MedicationDetail(BaseModel):
    medication_detail: str
    medication_import_date: datetime
    medication_source: int = 0

class MedicationHistory(BaseDocument):
    data: List[MedicationDetail]
    patient_id: PyObjectId

class BloodPressureData(BaseModel):
    systolic: Optional[float] = None
    diastolic: Optional[float] = None
    pulse: Optional[float] = None
    timestamp: datetime
    device_id: Optional[str] = None
    device_type: Optional[str] = None

class BloodPressureHistory(BaseDocument):
    patient_id: PyObjectId
    data: List[BloodPressureData]

class BloodSugarData(BaseModel):
    value: float
    unit: str = "mg/dL"
    timestamp: datetime
    device_id: Optional[str] = None
    device_type: Optional[str] = None
    meal_type: Optional[str] = None  # "before_meal", "after_meal", "fasting"

class BloodSugarHistory(BaseDocument):
    patient_id: PyObjectId
    data: List[BloodSugarData]

class BodyData(BaseModel):
    weight: Optional[float] = None
    height: Optional[float] = None
    bmi: Optional[float] = None
    body_fat: Optional[float] = None
    muscle_mass: Optional[float] = None
    timestamp: datetime
    device_id: Optional[str] = None
    device_type: Optional[str] = None

class BodyDataHistory(BaseDocument):
    patient_id: PyObjectId
    data: List[BodyData]

class CreatinineData(BaseModel):
    value: float
    unit: str = "mg/dL"
    timestamp: datetime
    device_id: Optional[str] = None
    device_type: Optional[str] = None

class CreatinineHistory(BaseDocument):
    patient_id: PyObjectId
    data: List[CreatinineData]

class LipidData(BaseModel):
    total_cholesterol: Optional[float] = None
    hdl: Optional[float] = None
    ldl: Optional[float] = None
    triglycerides: Optional[float] = None
    timestamp: datetime
    device_id: Optional[str] = None
    device_type: Optional[str] = None

class LipidHistory(BaseDocument):
    patient_id: PyObjectId
    data: List[LipidData]

class SleepData(BaseModel):
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    sleep_score: Optional[float] = None
    deep_sleep_minutes: Optional[int] = None
    light_sleep_minutes: Optional[int] = None
    rem_sleep_minutes: Optional[int] = None
    awake_minutes: Optional[int] = None
    device_id: Optional[str] = None
    device_type: Optional[str] = None

class SleepDataHistory(BaseDocument):
    patient_id: PyObjectId
    data: List[SleepData]

class Spo2Data(BaseModel):
    value: float
    timestamp: datetime
    device_id: Optional[str] = None
    device_type: Optional[str] = None

class Spo2History(BaseDocument):
    patient_id: PyObjectId
    data: List[Spo2Data]

class StepData(BaseModel):
    steps: int
    calories: Optional[float] = None
    distance: Optional[float] = None
    timestamp: datetime
    device_id: Optional[str] = None
    device_type: Optional[str] = None

class StepHistory(BaseDocument):
    patient_id: PyObjectId
    data: List[StepData]

class TemperatureData(BaseModel):
    value: float
    unit: str = "°C"
    timestamp: datetime
    device_id: Optional[str] = None
    device_type: Optional[str] = None

class TemperatureDataHistory(BaseDocument):
    patient_id: PyObjectId
    data: List[TemperatureData]

class AllergyData(BaseModel):
    allergen: str
    severity: Optional[str] = None
    symptoms: Optional[str] = None
    timestamp: datetime

class AllergyHistory(BaseDocument):
    patient_id: PyObjectId
    data: List[AllergyData]

class UnderlyingDiseaseData(BaseModel):
    disease_name: str
    diagnosis_date: Optional[datetime] = None
    severity: Optional[str] = None
    notes: Optional[str] = None
    timestamp: datetime

class UnderlyingDiseaseHistory(BaseDocument):
    patient_id: PyObjectId
    data: List[UnderlyingDiseaseData]

class AdmitData(BaseModel):
    hospital_name: str
    admit_date: datetime
    discharge_date: Optional[datetime] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    notes: Optional[str] = None

class AdmitDataHistory(BaseDocument):
    patient_id: PyObjectId
    data: List[AdmitData] 