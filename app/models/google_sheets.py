from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class GoogleSheetsIntegration(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    spreadsheet_id: str
    spreadsheet_title: str
    spreadsheet_url: str
    credentials_type: str  # 'service_account' or 'oauth2'
    credentials_data: str  # JSON string of credentials
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "spreadsheet_title": "VoiceConfirm Orders",
                "spreadsheet_url": "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "credentials_type": "service_account",
                "credentials_data": "{}",
                "is_active": True
            }
        }

class GoogleSheetsSetup(BaseModel):
    credentials_type: str = Field(..., description="Type of credentials: 'service_account' or 'oauth2'")
    credentials_data: str = Field(..., description="JSON string of Google credentials")
    spreadsheet_title: Optional[str] = Field("VoiceConfirm Orders", description="Title for new spreadsheet")
    existing_spreadsheet_id: Optional[str] = Field(None, description="ID of existing spreadsheet to use")

class GoogleSheetsResponse(BaseModel):
    success: bool
    message: str
    spreadsheet_id: Optional[str] = None
    spreadsheet_url: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class OrderImport(BaseModel):
    order_id: str
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    product_name: str
    quantity: int = 1
    total_amount: float
    order_date: Optional[str] = None
    notes: Optional[str] = None

class OrderUpdate(BaseModel):
    order_id: str
    call_status: str  # 'success', 'failed', 'no_answer', 'busy'
    confirmation_response: Optional[str] = None
    notes: Optional[str] = None

