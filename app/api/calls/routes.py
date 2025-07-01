from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional, Dict, Any
from app.models.call import Call, CallStats, CallFilters
from app.models.user import UserInDB
from app.services.auth_service import auth_service
from app.services.call_service import call_service
from app.services.elevenlabs_service import elevenlabs_service
from app.db.database import get_db

router = APIRouter()

@router.post("/{order_id}/initiate", response_model=Call)
async def initiate_call(
    order_id: str,
    language: str = Query("en", description="Language code for the call"),
    voice_id: Optional[str] = Query(None, description="ElevenLabs voice ID"),
    current_user: UserInDB = Depends(auth_service.get_current_active_user),
    db = Depends(get_db)
):
    """Initiate an order confirmation call."""
    call = await call_service.initiate_order_confirmation_call(
        order_id=order_id,
        user=current_user,
        db=db,
        language=language,
        voice_id=voice_id
    )
    return Call(**call.dict())

@router.get("/", response_model=List[Call])
async def get_calls(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    order_id: Optional[str] = Query(None),
    current_user: UserInDB = Depends(auth_service.get_current_active_user),
    db = Depends(get_db)
):
    """Get calls with optional filters."""
    filters = CallFilters(
        status=status,
        outcome=outcome,
        language=language,
        order_id=order_id
    )
    
    calls = await call_service.get_calls(current_user, db, filters, skip, limit)
    return [Call(**call.dict()) for call in calls]

@router.get("/stats", response_model=CallStats)
async def get_call_stats(
    current_user: UserInDB = Depends(auth_service.get_current_active_user),
    db = Depends(get_db)
):
    """Get call statistics."""
    stats = await call_service.get_call_stats(current_user, db)
    return stats

@router.get("/{call_id}", response_model=Call)
async def get_call(
    call_id: str,
    current_user: UserInDB = Depends(auth_service.get_current_active_user),
    db = Depends(get_db)
):
    """Get call by ID."""
    call = await call_service.get_call(call_id, current_user, db)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    return Call(**call.dict())

@router.get("/voices/available")
async def get_available_voices(
    current_user: UserInDB = Depends(auth_service.get_current_active_user)
):
    """Get available voices from ElevenLabs."""
    voices = await elevenlabs_service.get_voices()
    return {"voices": voices}

@router.get("/languages/supported")
async def get_supported_languages(
    current_user: UserInDB = Depends(auth_service.get_current_active_user)
):
    """Get supported languages."""
    languages = await elevenlabs_service.get_supported_languages()
    return {"languages": languages}

@router.post("/webhook/twilio")
async def twilio_webhook(request: Request, db = Depends(get_db)):
    """Handle Twilio webhook for call status updates."""
    try:
        # Get form data from Twilio webhook
        form_data = await request.form()
        webhook_data = dict(form_data)
        
        # Extract call ID from webhook data
        call_sid = webhook_data.get("CallSid")
        if not call_sid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing CallSid in webhook data"
            )
        
        # Process webhook
        success = await call_service.process_call_webhook(call_sid, webhook_data, db)
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to process webhook"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )

