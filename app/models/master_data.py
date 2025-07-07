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

class HospitalAddress(BaseModel):
    """Detailed address information for hospitals"""
    street_address: Optional[str] = Field(None, description="Street address including house/building number")
    building_name: Optional[str] = Field(None, description="Building or complex name")
    floor: Optional[str] = Field(None, description="Floor number if applicable")
    room: Optional[str] = Field(None, description="Room or suite number")
    postal_code: Optional[str] = Field(None, description="Postal/ZIP code")
    postal_box: Optional[str] = Field(None, description="P.O. Box if applicable")
    
class HospitalLocation(BaseModel):
    """Geographic location information"""
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    elevation: Optional[float] = Field(None, description="Elevation in meters")
    precision: Optional[str] = Field(None, description="GPS precision/accuracy")
    
class HospitalContact(BaseModel):
    """Contact information for hospitals"""
    phone: Optional[str] = Field(None, description="Primary phone number")
    phone_2: Optional[str] = Field(None, description="Secondary phone number")
    fax: Optional[str] = Field(None, description="Fax number")
    mobile: Optional[str] = Field(None, description="Mobile phone number")
    emergency_phone: Optional[str] = Field(None, description="Emergency contact number")
    email: Optional[str] = Field(None, description="Primary email address")
    email_admin: Optional[str] = Field(None, description="Administrative email")
    website: Optional[str] = Field(None, description="Hospital website URL")
    
class HospitalServices(BaseModel):
    """Hospital service and administrative information"""
    bed_capacity: Optional[int] = Field(None, description="Total number of beds")
    emergency_services: Optional[bool] = Field(None, description="24/7 emergency services available")
    trauma_center: Optional[bool] = Field(None, description="Trauma center designation")
    icu_beds: Optional[int] = Field(None, description="ICU bed capacity")
    operating_rooms: Optional[int] = Field(None, description="Number of operating rooms")
    service_plan_type: Optional[str] = Field(None, description="Service plan classification")
    accreditation: Optional[str] = Field(None, description="Hospital accreditation status")
    
class Hospital(BaseDocument):
    # Basic Identification
    code: str = Field(..., description="Hospital code identifier")
    name: NameModel = Field(..., description="Hospital name in multiple languages")
    hospital_type_id: Optional[PyObjectId] = Field(None, description="Reference to hospital type")
    organizecode: Optional[int] = Field(None, description="Organization code")
    hospital_area_code: Optional[str] = Field(None, description="Hospital area code")
    
    # Geographic Location
    province_code: str = Field(..., description="Province code")
    district_code: str = Field(..., description="District code")  
    sub_district_code: str = Field(..., description="Sub-district code")
    
    # Detailed Address Information
    address: Optional[str] = Field(None, description="Basic address string")
    address_details: Optional[HospitalAddress] = Field(None, description="Detailed address components")
    location: Optional[HospitalLocation] = Field(None, description="Geographic coordinates")
    
    # Contact Information
    contact: Optional[HospitalContact] = Field(None, description="Contact details")
    
    # Legacy contact fields (for backward compatibility)
    phone: Optional[str] = Field(None, description="Primary phone (legacy field)")
    email: Optional[str] = Field(None, description="Primary email (legacy field)")
    website: Optional[str] = Field(None, description="Website (legacy field)")
    
    # Service Information
    services: Optional[HospitalServices] = Field(None, description="Hospital services and capacity")
    
    # Legacy service fields (for backward compatibility)
    bed_capacity: Optional[int] = Field(None, description="Bed capacity (legacy field)")
    service_plan_type: Optional[str] = Field(None, description="Service plan (legacy field)")
    
    # Device Integration
    mac_hv01_box: Optional[str] = Field(None, description="Qube-Vital box MAC address")
    
    # Digital Integration
    image_url: Optional[str] = Field(None, description="Hospital image/logo URL")
    auto_login_liff_id: Optional[str] = Field(None, description="LINE auto-login LIFF ID")
    disconnect_liff_id: Optional[str] = Field(None, description="LINE disconnect LIFF ID")
    login_liff_id: Optional[str] = Field(None, description="LINE login LIFF ID")
    notifyToken: Optional[str] = Field(None, description="LINE notification token")
    
    # Status
    active: bool = Field(True, description="Hospital active status")
    is_active: Optional[bool] = Field(None, description="Alternative active field")
    is_deleted: Optional[bool] = Field(False, description="Soft delete flag") 