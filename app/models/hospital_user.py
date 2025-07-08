from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from .base import BaseDocument, PyObjectId

class HospitalUserBase(BaseModel):
    """Base model for hospital user"""
    email: EmailStr
    first_name: str
    last_name: str
    user_title: str = Field(default="Mr.", description="Title: Mr., Mrs., Miss, Dr., other")
    phone: str
    country_phone_code: str = Field(default="+66")
    country_code: str = Field(default="Th")
    country_name: str = Field(default="Thailand")
    hospital_id: PyObjectId
    type: PyObjectId  # User type reference
    
    # Optional fields
    image_url: Optional[str] = ""
    server_token: Optional[str] = ""
    device_token: Optional[str] = ""
    device_type: Optional[str] = ""
    app_version: Optional[str] = ""

class HospitalUserCreate(HospitalUserBase):
    """Model for creating a new hospital user"""
    password: str = Field(..., min_length=6, description="Password (will be hashed)")

class HospitalUserUpdate(BaseModel):
    """Model for updating hospital user"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_title: Optional[str] = None
    phone: Optional[str] = None
    country_phone_code: Optional[str] = None
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    hospital_id: Optional[PyObjectId] = None
    type: Optional[PyObjectId] = None
    image_url: Optional[str] = None
    server_token: Optional[str] = None
    device_token: Optional[str] = None
    device_type: Optional[str] = None
    app_version: Optional[str] = None

class HospitalUser(BaseDocument):
    """Complete hospital user model"""
    # Basic Information
    email: EmailStr
    password: str  # Hashed password
    first_name: str
    last_name: str
    user_title: str = Field(default="Mr.")
    phone: str
    country_phone_code: str = Field(default="+66")
    country_code: str = Field(default="Th")
    country_name: str = Field(default="Thailand")
    
    # References
    hospital_id: PyObjectId
    type: PyObjectId  # User type reference
    
    # Optional fields
    image_url: Optional[str] = ""
    server_token: Optional[str] = ""
    device_token: Optional[str] = ""
    device_type: Optional[str] = ""
    app_version: Optional[str] = ""
    
    # System fields
    unique_id: Optional[int] = None
    version: Optional[int] = Field(default=0, alias="__v")
    
    # Status fields
    is_active: bool = True
    is_deleted: bool = False

class HospitalUserResponse(BaseModel):
    """Model for hospital user API responses"""
    id: str = Field(alias="_id")
    email: str
    first_name: str
    last_name: str
    user_title: str
    phone: str
    country_phone_code: str
    country_code: str
    country_name: str
    hospital_id: str
    type: str
    image_url: Optional[str]
    server_token: Optional[str]
    device_token: Optional[str]
    device_type: Optional[str]
    app_version: Optional[str]
    unique_id: Optional[int]
    is_active: bool
    is_deleted: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    model_config = {"populate_by_name": True}

class HospitalUserList(BaseModel):
    """Model for paginated hospital user list"""
    users: List[HospitalUserResponse]
    total: int
    limit: int
    skip: int
    has_next: bool
    has_prev: bool

class HospitalUserSearchQuery(BaseModel):
    """Model for hospital user search parameters"""
    hospital_id: Optional[str] = None
    type: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None
    search: Optional[str] = None  # General search across name and email

class HospitalUserStats(BaseModel):
    """Model for hospital user statistics"""
    total_users: int
    active_users: int
    inactive_users: int
    deleted_users: int
    users_by_hospital: dict
    users_by_type: dict 