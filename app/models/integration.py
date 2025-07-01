from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from .user import PyObjectId

class IntegrationBase(BaseModel):
    platform: str  # shopify, woocommerce, google_sheets, custom
    name: str
    description: Optional[str] = None
    is_active: bool = True
    settings: Dict[str, Any] = {}
    credentials: Dict[str, Any] = {}  # This will be encrypted
    webhook_url: Optional[str] = None
    sync_frequency: str = "real_time"  # real_time, hourly, daily, manual
    last_sync_status: str = "never"  # never, success, failed, in_progress
    error_message: Optional[str] = None

class IntegrationCreate(IntegrationBase):
    user_id: PyObjectId

class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None
    webhook_url: Optional[str] = None
    sync_frequency: Optional[str] = None

class IntegrationInDB(IntegrationBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_sync: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class Integration(IntegrationBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    created_at: datetime
    updated_at: datetime
    last_sync: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Specific integration configurations
class ShopifyConfig(BaseModel):
    shop_url: str
    access_token: str
    webhook_secret: Optional[str] = None
    auto_import_orders: bool = True
    order_statuses: list = ["pending", "confirmed"]

class WooCommerceConfig(BaseModel):
    site_url: str
    consumer_key: str
    consumer_secret: str
    webhook_secret: Optional[str] = None
    auto_import_orders: bool = True
    order_statuses: list = ["pending", "processing"]

class GoogleSheetsConfig(BaseModel):
    spreadsheet_id: str
    sheet_name: str = "Orders"
    credentials_file: str
    column_mapping: Dict[str, str] = {
        "order_id": "A",
        "customer_name": "B",
        "customer_phone": "C",
        "customer_email": "D",
        "total": "E",
        "status": "F"
    }
    auto_sync: bool = True

class IntegrationStats(BaseModel):
    total_integrations: int
    active_integrations: int
    failed_integrations: int
    last_sync_times: Dict[str, Optional[datetime]]
    sync_success_rates: Dict[str, float]

