from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from .base import BaseDocument, PyObjectId

class Patient(BaseDocument):
    # Basic Information
    first_name: str
    last_name: str
    nickname: Optional[str] = None
    gender: str  # "male", "female"
    birth_date: Optional[datetime] = None
    id_card: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    
    # Address Information
    address: Optional[str] = None
    province_code: Optional[str] = None
    district_code: Optional[str] = None
    sub_district_code: Optional[str] = None
    postal_code: Optional[str] = None
    
    # Emergency Contact
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    
    # Medical Information
    blood_type: Optional[str] = None
    height: Optional[float] = None  # cm
    weight: Optional[float] = None  # kg
    bmi: Optional[float] = None
    
    # Device Mappings
    watch_mac_address: Optional[str] = None  # Kati Watch
    ava_mac_address: Optional[str] = None   # AVA4 Box
    new_hospital_ids: Optional[List[PyObjectId]] = None
    
    # Status
    is_active: bool = True
    is_deleted: bool = False
    
    # Additional fields from JSON
    unique_id: Optional[int] = None
    version: Optional[int] = Field(default=0, alias="__v") 