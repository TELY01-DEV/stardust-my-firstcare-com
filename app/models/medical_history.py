from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from .base import BaseDocument, PyObjectId

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