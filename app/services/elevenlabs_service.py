import httpx
import asyncio
from typing import Optional, Dict, Any, List
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ElevenLabsService:
    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "Accept": "application/json",
            "xi-api-key": self.api_key
        }
    
    async def get_voices(self) -> List[Dict[str, Any]]:
        """Get available voices from ElevenLabs."""
        if not self.api_key:
            logger.warning("ElevenLabs API key not configured")
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()
                return data.get("voices", [])
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return []
    
    async def text_to_speech(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Default voice
        model_id: str = "eleven_monolingual_v1",
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Optional[bytes]:
        """Convert text to speech using ElevenLabs API."""
        if not self.api_key:
            logger.warning("ElevenLabs API key not configured")
            return None
        
        if voice_settings is None:
            voice_settings = {
                "stability": 0.5,
                "similarity_boost": 0.5,
                "style": 0.0,
                "use_speaker_boost": True
            }
        
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": voice_settings
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.content
        except Exception as e:
            logger.error(f"Failed to convert text to speech: {e}")
            return None
    
    async def create_conversation_audio(
        self,
        script: str,
        voice_id: str,
        language: str = "en",
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Optional[bytes]:
        """Create conversation audio for order confirmation."""
        # Customize script based on language
        localized_script = await self.localize_script(script, language)
        
        # Generate audio
        audio_data = await self.text_to_speech(
            text=localized_script,
            voice_id=voice_id,
            voice_settings=voice_settings
        )
        
        return audio_data
    
    async def localize_script(self, script: str, language: str) -> str:
        """Localize script based on language."""
        # This is a simplified version - in production, you'd use proper translation
        language_greetings = {
            "en": "Hello",
            "es": "Hola",
            "fr": "Bonjour",
            "de": "Hallo",
            "it": "Ciao",
            "pt": "Olá",
            "ru": "Привет",
            "zh": "你好",
            "ja": "こんにちは",
            "ko": "안녕하세요",
            "ar": "مرحبا",
            "hi": "नमस्ते",
            "ur": "السلام علیکم"
        }
        
        greeting = language_greetings.get(language, "Hello")
        
        # Replace greeting in script
        if script.startswith("Hello"):
            script = script.replace("Hello", greeting, 1)
        
        return script
    
    async def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages."""
        # This would typically come from ElevenLabs API
        # For now, returning a static list of common languages
        return [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "it", "name": "Italian"},
            {"code": "pt", "name": "Portuguese"},
            {"code": "ru", "name": "Russian"},
            {"code": "zh", "name": "Chinese"},
            {"code": "ja", "name": "Japanese"},
            {"code": "ko", "name": "Korean"},
            {"code": "ar", "name": "Arabic"},
            {"code": "hi", "name": "Hindi"},
            {"code": "ur", "name": "Urdu"},
            {"code": "nl", "name": "Dutch"},
            {"code": "pl", "name": "Polish"},
            {"code": "tr", "name": "Turkish"},
            {"code": "sv", "name": "Swedish"},
            {"code": "no", "name": "Norwegian"},
            {"code": "da", "name": "Danish"},
            {"code": "fi", "name": "Finnish"}
        ]
    
    async def generate_confirmation_script(
        self,
        customer_name: str,
        order_id: str,
        order_total: float,
        currency: str = "USD",
        items: List[Dict[str, Any]] = None,
        language: str = "en"
    ) -> str:
        """Generate order confirmation script."""
        if items is None:
            items = []
        
        # Create items summary
        items_text = ""
        if items:
            items_list = []
            for item in items[:3]:  # Limit to first 3 items
                items_list.append(f"{item.get('quantity', 1)} {item.get('name', 'item')}")
            items_text = f"including {', '.join(items_list)}"
            if len(items) > 3:
                items_text += f" and {len(items) - 3} more items"
        
        # Base script template
        script_template = """Hello {customer_name}, this is a call from VoiceConfirm regarding your recent order #{order_id}. 

I'm calling to confirm your order totaling {total} {currency} {items_text}. 

Could you please confirm that you placed this order and that all the details are correct? 

If you confirm this order, please say 'yes' or 'confirm'. If there are any issues or you need to cancel, please say 'no' or 'cancel'.

Thank you for your time."""
        
        script = script_template.format(
            customer_name=customer_name,
            order_id=order_id,
            total=order_total,
            currency=currency,
            items_text=items_text
        )
        
        return script

# Create service instance
elevenlabs_service = ElevenLabsService()

