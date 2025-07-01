from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from bson import ObjectId
from .user import PyObjectId

class CallBase(BaseModel):
    call_id: str  # Unique call identifier
    order_id: PyObjectId
    user_id: PyObjectId
    status: str = "initiated"  # initiated, in_progress, completed, failed, cancelled
    call_type: str = "confirmation"  # confirmation, follow_up, callback
    language: str = "en"
    voice_id: Optional[str] = None
    duration: Optional[int] = None  # Duration in seconds
    transcript: Optional[str] = None
    audio_url: Optional[str] = None
    outcome: Optional[str] = None  # confirmed, rejected, no_answer, callback_requested, invalid_number
    customer_response: Optional[str] = None
    ai_confidence: Optional[float] = None
    retry_count: int = 0
    scheduled_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class CallCreate(CallBase):
    pass

class CallUpdate(BaseModel):
    status: Optional[str] = None
    duration: Optional[int] = None
    transcript: Optional[str] = None
    audio_url: Optional[str] = None
    outcome: Optional[str] = None
    customer_response: Optional[str] = None
    ai_confidence: Optional[float] = None
    retry_count: Optional[int] = None

class CallInDB(CallBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class Call(CallBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class CallStats(BaseModel):
    total_calls: int
    successful_calls: int
    failed_calls: int
    average_duration: float
    success_rate: float
    total_duration: int
    calls_by_outcome: Dict[str, int]
    calls_by_language: Dict[str, int]

class CallFilters(BaseModel):
    status: Optional[str] = None
    outcome: Optional[str] = None
    language: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    order_id: Optional[str] = None

class VoiceSettings(BaseModel):
    voice_id: str
    stability: float = 0.5
    similarity_boost: float = 0.5
    style: float = 0.0
    use_speaker_boost: bool = True

class CallScript(BaseModel):
    greeting: str
    order_confirmation: str
    address_confirmation: str
    payment_confirmation: str
    closing: str
    fallback_responses: List[str]

