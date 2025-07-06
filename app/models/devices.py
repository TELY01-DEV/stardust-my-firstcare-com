from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from .base import BaseDocument, PyObjectId

class AmyBox(BaseDocument):
    """AVA4 Box Model"""
    box_name: str
    ip_address: Optional[str] = None
    mac_address: str
    location: Optional[str] = None
    sim_number: Optional[str] = None
    provider: Optional[str] = None
    lat: float = 0
    lng: float = 0
    version: Optional[str] = None
    model: str = "M5-AVA3"
    factory: Optional[str] = None
    wireless_ip: Optional[str] = None
    ethernet_ip: Optional[str] = None
    uplink_type: Optional[str] = Field(None, alias="uplinkType")
    box_type: int = 0
    is_have_bluetooth_connection: bool = False
    is_required_registration: bool = False
    status: int = 0
    heart_count: int = 0
    data_update_time: Optional[datetime] = None
    gw_send_time: Optional[str] = None
    is_active: bool = False
    is_deleted: bool = False
    uptime_updated_at: Optional[datetime] = None
    unique_id: Optional[int] = None
    version_num: Optional[int] = Field(default=0, alias="__v")
    patient_id: Optional[PyObjectId] = None
    uptime: int = 0

class AmyDevice(BaseDocument):
    """AVA4 Sub-device Model"""
    device_name: Optional[str] = None
    mac_address: str
    device_type: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None
    status: int = 0
    is_active: bool = False
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    unique_id: Optional[int] = None
    version_num: Optional[int] = Field(default=0, alias="__v")
    box_id: Optional[PyObjectId] = None  # Reference to amy_boxes
    patient_id: Optional[PyObjectId] = None

class Watch(BaseDocument):
    """Kati Watch Model"""
    user_id: Optional[PyObjectId] = None
    patient_id: Optional[PyObjectId] = None
    imei: str
    factory: Optional[str] = None
    model: Optional[str] = None
    mobile_no: Optional[str] = None
    auto_vital_sign_minutes: int = 20
    is_auto_vital_sign: bool = True
    location_update_minutes: int = 1
    working_mode: int = 3
    status: str = "offline"
    auto_temprature_minutes: int = 0
    is_auto_sleep_monitoring: bool = False
    is_auto_temprature: bool = False
    sleep_setting: Optional[str] = None
    battery: int = 0
    signal_gsm: int = Field(0, alias="signalGSM")
    unique_id: Optional[int] = None
    version_num: Optional[int] = Field(default=0, alias="__v")

class MfcHv01Box(BaseDocument):
    """Qube-Vital Model"""
    box_name: str
    imei_of_hv01_box: str
    hospital_id: Optional[PyObjectId] = None
    status: str = "offline"
    is_active: bool = False
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    unique_id: Optional[int] = None
    version_num: Optional[int] = Field(default=0, alias="__v") 