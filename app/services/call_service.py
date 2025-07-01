from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException, status
import uuid
import asyncio

from app.models.call import CallCreate, CallUpdate, CallInDB, Call, CallStats, CallFilters
from app.models.order import OrderInDB
from app.models.user import UserInDB
from app.services.elevenlabs_service import elevenlabs_service
from app.services.twilio_service import twilio_service
import logging

logger = logging.getLogger(__name__)

class CallService:
    def __init__(self):
        pass
    
    async def create_call(self, call_data: CallCreate, db) -> CallInDB:
        """Create a new call record."""
        try:
            # Generate unique call ID
            call_data.call_id = str(uuid.uuid4())
            
            # Create call document
            call_dict = call_data.dict()
            call_dict["created_at"] = datetime.utcnow()
            call_dict["updated_at"] = datetime.utcnow()
            
            # Insert call
            result = await db.call_logs.insert_one(call_dict)
            call_dict["_id"] = result.inserted_id
            
            logger.info(f"Created call record {call_data.call_id}")
            return CallInDB(**call_dict)
            
        except Exception as e:
            logger.error(f"Failed to create call record: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create call record"
            )
    
    async def initiate_order_confirmation_call(
        self,
        order_id: str,
        user: UserInDB,
        db,
        language: str = "en",
        voice_id: Optional[str] = None
    ) -> CallInDB:
        """Initiate an order confirmation call."""
        try:
            # Get order details
            order = await db.orders.find_one({
                "_id": ObjectId(order_id),
                "user_id": user.id
            })
            
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found"
                )
            
            order_obj = OrderInDB(**order)
            
            # Check if order can be called
            if order_obj.confirmation_status == "confirmed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Order already confirmed"
                )
            
            if order_obj.call_attempts >= order_obj.max_call_attempts:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum call attempts reached"
                )
            
            # Use default voice if not specified
            if not voice_id:
                voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default ElevenLabs voice
            
            # Create call record
            call_data = CallCreate(
                call_id="",  # Will be generated
                order_id=ObjectId(order_id),
                user_id=user.id,
                status="initiated",
                language=language,
                voice_id=voice_id,
                scheduled_at=datetime.utcnow()
            )
            
            call_record = await self.create_call(call_data, db)
            
            # Generate confirmation script
            script = await elevenlabs_service.generate_confirmation_script(
                customer_name=order_obj.customer.name,
                order_id=order_obj.order_id,
                order_total=order_obj.order_details.total,
                currency=order_obj.order_details.currency,
                items=[item.dict() for item in order_obj.order_details.items],
                language=language
            )
            
            # Generate audio
            audio_data = await elevenlabs_service.create_conversation_audio(
                script=script,
                voice_id=voice_id,
                language=language
            )
            
            if not audio_data:
                # Update call status to failed
                await self.update_call(
                    call_record.id,
                    CallUpdate(
                        status="failed",
                        outcome="audio_generation_failed"
                    ),
                    db
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate audio"
                )
            
            # Make the call via Twilio/WhatsApp
            call_result = await twilio_service.make_voice_call(
                phone_number=order_obj.customer.phone,
                audio_data=audio_data,
                call_id=call_record.call_id
            )
            
            # Update call record with results
            call_update = CallUpdate(
                status="in_progress" if call_result.get("success") else "failed",
                started_at=datetime.utcnow(),
                transcript=script,
                metadata=call_result
            )
            
            updated_call = await self.update_call(call_record.id, call_update, db)
            
            # Update order call attempts
            await db.orders.update_one(
                {"_id": ObjectId(order_id)},
                {
                    "$inc": {"call_attempts": 1},
                    "$set": {"last_call_date": datetime.utcnow()}
                }
            )
            
            logger.info(f"Initiated call for order {order_id}")
            return updated_call
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to initiate call for order {order_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate call"
            )
    
    async def update_call(self, call_id: str, call_update: CallUpdate, db) -> Optional[CallInDB]:
        """Update call record."""
        try:
            # Prepare update data
            update_data = call_update.dict(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow()
            
            # Special handling for status changes
            if "status" in update_data:
                if update_data["status"] == "completed":
                    update_data["ended_at"] = datetime.utcnow()
            
            # Update call
            result = await db.call_logs.update_one(
                {"_id": ObjectId(call_id)},
                {"$set": update_data}
            )
            
            if result.modified_count == 0:
                return None
            
            # Get updated call
            updated_call = await db.call_logs.find_one({"_id": ObjectId(call_id)})
            logger.info(f"Updated call {call_id}")
            
            return CallInDB(**updated_call)
            
        except Exception as e:
            logger.error(f"Failed to update call {call_id}: {e}")
            return None
    
    async def get_call(self, call_id: str, user: UserInDB, db) -> Optional[CallInDB]:
        """Get call by ID."""
        try:
            query = {"_id": ObjectId(call_id)}
            
            # Non-admin users can only see their own calls
            if user.role != "admin":
                query["user_id"] = user.id
            
            call = await db.call_logs.find_one(query)
            if not call:
                return None
            
            return CallInDB(**call)
            
        except Exception as e:
            logger.error(f"Failed to get call {call_id}: {e}")
            return None
    
    async def get_calls(
        self,
        user: UserInDB,
        db,
        filters: Optional[CallFilters] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[CallInDB]:
        """Get calls with optional filters."""
        try:
            query = {}
            
            # Non-admin users can only see their own calls
            if user.role != "admin":
                query["user_id"] = user.id
            
            # Apply filters
            if filters:
                if filters.status:
                    query["status"] = filters.status
                if filters.outcome:
                    query["outcome"] = filters.outcome
                if filters.language:
                    query["language"] = filters.language
                if filters.order_id:
                    query["order_id"] = ObjectId(filters.order_id)
                if filters.date_from or filters.date_to:
                    date_query = {}
                    if filters.date_from:
                        date_query["$gte"] = filters.date_from
                    if filters.date_to:
                        date_query["$lte"] = filters.date_to
                    query["created_at"] = date_query
            
            # Execute query
            cursor = db.call_logs.find(query).sort("created_at", -1).skip(skip).limit(limit)
            calls = await cursor.to_list(length=limit)
            
            return [CallInDB(**call) for call in calls]
            
        except Exception as e:
            logger.error(f"Failed to get calls: {e}")
            return []
    
    async def get_call_stats(self, user: UserInDB, db) -> CallStats:
        """Get call statistics."""
        try:
            query = {}
            
            # Non-admin users can only see their own stats
            if user.role != "admin":
                query["user_id"] = user.id
            
            # Aggregate statistics
            pipeline = [
                {"$match": query},
                {
                    "$group": {
                        "_id": None,
                        "total_calls": {"$sum": 1},
                        "successful_calls": {
                            "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                        },
                        "failed_calls": {
                            "$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}
                        },
                        "total_duration": {"$sum": "$duration"},
                        "outcomes": {"$push": "$outcome"},
                        "languages": {"$push": "$language"}
                    }
                }
            ]
            
            result = await db.call_logs.aggregate(pipeline).to_list(length=1)
            
            if result:
                stats = result[0]
                total_calls = stats["total_calls"]
                successful_calls = stats["successful_calls"]
                total_duration = stats["total_duration"] or 0
                
                success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
                average_duration = (total_duration / total_calls) if total_calls > 0 else 0
                
                # Count outcomes
                outcomes = stats["outcomes"]
                calls_by_outcome = {}
                for outcome in outcomes:
                    if outcome:
                        calls_by_outcome[outcome] = calls_by_outcome.get(outcome, 0) + 1
                
                # Count languages
                languages = stats["languages"]
                calls_by_language = {}
                for language in languages:
                    if language:
                        calls_by_language[language] = calls_by_language.get(language, 0) + 1
                
                return CallStats(
                    total_calls=total_calls,
                    successful_calls=successful_calls,
                    failed_calls=stats["failed_calls"],
                    average_duration=round(average_duration, 2),
                    success_rate=round(success_rate, 2),
                    total_duration=total_duration,
                    calls_by_outcome=calls_by_outcome,
                    calls_by_language=calls_by_language
                )
            else:
                return CallStats(
                    total_calls=0,
                    successful_calls=0,
                    failed_calls=0,
                    average_duration=0.0,
                    success_rate=0.0,
                    total_duration=0,
                    calls_by_outcome={},
                    calls_by_language={}
                )
                
        except Exception as e:
            logger.error(f"Failed to get call stats: {e}")
            return CallStats(
                total_calls=0,
                successful_calls=0,
                failed_calls=0,
                average_duration=0.0,
                success_rate=0.0,
                total_duration=0,
                calls_by_outcome={},
                calls_by_language={}
            )
    
    async def process_call_webhook(self, call_id: str, webhook_data: Dict[str, Any], db) -> bool:
        """Process webhook data from call provider."""
        try:
            # Find call record
            call = await db.call_logs.find_one({"call_id": call_id})
            if not call:
                logger.warning(f"Call {call_id} not found for webhook processing")
                return False
            
            # Extract relevant data from webhook
            status = webhook_data.get("CallStatus", "unknown")
            duration = webhook_data.get("CallDuration", 0)
            
            # Map Twilio status to our status
            status_mapping = {
                "completed": "completed",
                "busy": "failed",
                "no-answer": "failed",
                "failed": "failed",
                "canceled": "cancelled"
            }
            
            mapped_status = status_mapping.get(status, "failed")
            
            # Determine outcome based on status and duration
            outcome = "no_answer"
            if mapped_status == "completed" and int(duration) > 10:
                outcome = "completed"  # Assume confirmed if call lasted more than 10 seconds
            elif mapped_status == "failed":
                outcome = "failed"
            
            # Update call record
            update_data = {
                "status": mapped_status,
                "duration": int(duration),
                "outcome": outcome,
                "updated_at": datetime.utcnow(),
                "metadata": webhook_data
            }
            
            if mapped_status == "completed":
                update_data["ended_at"] = datetime.utcnow()
            
            await db.call_logs.update_one(
                {"call_id": call_id},
                {"$set": update_data}
            )
            
            # Update related order if call was successful
            if outcome == "completed":
                await db.orders.update_one(
                    {"_id": call["order_id"]},
                    {"$set": {"confirmation_status": "confirmed", "confirmed_at": datetime.utcnow()}}
                )
            
            logger.info(f"Processed webhook for call {call_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process webhook for call {call_id}: {e}")
            return False

# Create service instance
call_service = CallService()

