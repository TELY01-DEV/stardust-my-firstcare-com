from typing import Optional, List
from pydantic import BaseModel, Field
from .base import BaseDocument, NameModel, PyObjectId

class MasterHospitalType(BaseDocument):
    name: NameModel
    active: bool = True

class Province(BaseDocument):
    code: str
    name: NameModel
    active: bool = True

class District(BaseDocument):
    code: str
    name: NameModel
    province_code: str
    active: bool = True

class SubDistrict(BaseDocument):
    code: str
    name: NameModel
    district_code: str
    province_code: str
    active: bool = True

class Hospital(BaseDocument):
    code: str
    name: NameModel
    hospital_type_id: Optional[PyObjectId] = None
    province_code: str
    district_code: str
    sub_district_code: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    active: bool = True
    mac_hv01_box: Optional[str] = None  # For Qube-Vital mapping 