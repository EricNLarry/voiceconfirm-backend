from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from .user import PyObjectId

class OrderCustomer(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[Dict[str, Any]] = None

class OrderItem(BaseModel):
    name: str
    quantity: int
    price: float
    sku: Optional[str] = None
    image_url: Optional[str] = None

class OrderDetails(BaseModel):
    items: List[OrderItem]
    total: float
    currency: str = "USD"
    order_date: datetime
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None

class OrderBase(BaseModel):
    order_id: str  # External order ID from e-commerce platform
    customer: OrderCustomer
    order_details: OrderDetails
    confirmation_status: str = "pending"  # pending, confirmed, failed, cancelled
    call_attempts: int = 0
    max_call_attempts: int = 3
    priority: str = "normal"  # low, normal, high, urgent
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class OrderCreate(OrderBase):
    user_id: PyObjectId

class OrderUpdate(BaseModel):
    confirmation_status: Optional[str] = None
    call_attempts: Optional[int] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    last_call_date: Optional[datetime] = None

class OrderInDB(OrderBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_call_date: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class Order(OrderBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    created_at: datetime
    updated_at: datetime
    last_call_date: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class OrderStats(BaseModel):
    total_orders: int
    pending_orders: int
    confirmed_orders: int
    failed_orders: int
    cancelled_orders: int
    confirmation_rate: float
    average_call_attempts: float

class OrderFilters(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    customer_name: Optional[str] = None
    order_id: Optional[str] = None

