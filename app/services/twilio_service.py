import base64
import tempfile
import os
from typing import Optional, Dict, Any
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.whatsapp_number = settings.twilio_whatsapp_number
        self.client = None
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
    
    async def make_voice_call(
        self,
        phone_number: str,
        audio_data: bytes,
        call_id: str,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make a voice call using Twilio."""
        if not self.client:
            logger.warning("Twilio client not configured")
            return {"success": False, "error": "Twilio not configured"}
        
        try:
            # For demo purposes, we'll simulate a successful call
            # In production, you would:
            # 1. Upload audio to a publicly accessible URL
            # 2. Create TwiML that plays the audio
            # 3. Make the call using Twilio's API
            
            # Simulate call creation
            result = {
                "success": True,
                "call_sid": f"CA{call_id[:32]}",
                "status": "initiated",
                "to": phone_number,
                "from": self.whatsapp_number or "+1234567890"
            }
            
            logger.info(f"Simulated voice call to {phone_number} for call {call_id}")
            return result
            
        except TwilioException as e:
            logger.error(f"Twilio error making call: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Failed to make voice call: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_whatsapp_message(
        self,
        phone_number: str,
        message: str,
        media_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send WhatsApp message using Twilio."""
        if not self.client:
            logger.warning("Twilio client not configured")
            return {"success": False, "error": "Twilio not configured"}
        
        try:
            # Format phone number for WhatsApp
            if not phone_number.startswith("whatsapp:"):
                phone_number = f"whatsapp:{phone_number}"
            
            message_data = {
                "body": message,
                "from": self.whatsapp_number,
                "to": phone_number
            }
            
            if media_url:
                message_data["media_url"] = [media_url]
            
            message_obj = self.client.messages.create(**message_data)
            
            return {
                "success": True,
                "message_sid": message_obj.sid,
                "status": message_obj.status
            }
            
        except TwilioException as e:
            logger.error(f"Twilio error sending WhatsApp message: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """Get call status from Twilio."""
        if not self.client:
            return {"error": "Twilio not configured"}
        
        try:
            call = self.client.calls(call_sid).fetch()
            
            return {
                "sid": call.sid,
                "status": call.status,
                "duration": call.duration,
                "start_time": call.start_time,
                "end_time": call.end_time,
                "price": call.price,
                "direction": call.direction
            }
            
        except TwilioException as e:
            logger.error(f"Twilio error getting call status: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Failed to get call status: {e}")
            return {"error": str(e)}
    
    async def upload_audio_to_public_url(self, audio_data: bytes, filename: str) -> Optional[str]:
        """Upload audio to a publicly accessible URL."""
        # This is a placeholder implementation
        # In production, you would upload to AWS S3, Google Cloud Storage, etc.
        # and return the public URL
        
        try:
            # For demo purposes, we'll save to a temporary file
            # In production, replace this with actual cloud storage upload
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, filename)
            
            with open(file_path, "wb") as f:
                f.write(audio_data)
            
            # Return a placeholder URL
            # In production, this would be the actual public URL
            public_url = f"https://your-domain.com/audio/{filename}"
            
            logger.info(f"Audio uploaded to {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload audio: {e}")
            return None
    
    def validate_webhook_signature(self, signature: str, url: str, params: Dict[str, Any]) -> bool:
        """Validate Twilio webhook signature."""
        if not self.auth_token:
            return False
        
        try:
            from twilio.request_validator import RequestValidator
            validator = RequestValidator(self.auth_token)
            return validator.validate(url, params, signature)
        except Exception as e:
            logger.error(f"Failed to validate webhook signature: {e}")
            return False

# Create service instance
twilio_service = TwilioService()

