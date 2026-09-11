import logging
import time
from typing import List, Optional
from google import genai
from app.config import settings

logger = logging.getLogger("GeminiKeyManager")

class GeminiKeyManager:
    """
    Service responsible for loading, round-robin load balancing,
    and automatic failover across multiple configured Gemini API keys.
    """
    def __init__(self):
        self.keys: List[str] = settings.GEMINI_API_KEYS
        self.current_index: int = 0
        # Tracks failed key indices and cooldown timestamp
        self.key_status: dict = {}  # {index: cooldown_until_timestamp}
        self.cooldown_seconds: int = 60 * 5  # 5 minutes cooldown for failing keys

    def get_client(self) -> tuple[Optional[genai.Client], Optional[int]]:
        """
        Retrieves a valid google.genai.Client using the next available API key.
        Returns (Client, key_index) or (None, None) if no keys are configured/available.
        """
        # Always refresh keys list from settings
        self.keys = settings.GEMINI_API_KEYS
        if not self.keys:
            logger.warning("[AI DIAGNOSTIC] Gemini API keys configured: NO")
            return None, None

        num_keys = len(self.keys)
        now = time.time()

        for _ in range(num_keys):
            idx = self.current_index
            self.current_index = (self.current_index + 1) % num_keys

            # Check if key is in cooldown
            cooldown_until = self.key_status.get(idx, 0)
            if now < cooldown_until:
                logger.info(f"[AI DIAGNOSTIC] Skipping Gemini Key #{idx + 1} (in cooldown for {int(cooldown_until - now)}s)")
                continue

            api_key = self.keys[idx]
            try:
                # Initialize GenAI Client with 30-second timeout protection
                client = genai.Client(
                    api_key=api_key,
                    http_options=genai.types.HttpOptions(timeout=30000)
                )
                return client, idx
            except Exception as e:
                logger.error(f"[AI DIAGNOSTIC] Failed to instantiate client for Gemini Key #{idx + 1}: {str(e)}")
                self.mark_key_failed(idx, duration=30)

        logger.error("[AI DIAGNOSTIC] All configured Gemini API keys are currently failing or unavailable.")
        return None, None

    def mark_key_failed(self, idx: int, duration: int = 30):
        """Temporarily marks key as unavailable for short cooldown period."""
        if 0 <= idx < len(self.keys):
            cooldown_until = time.time() + duration
            self.key_status[idx] = cooldown_until
            logger.warning(f"[AI DIAGNOSTIC] Gemini Key #{idx + 1} marked unavailable for {duration}s.")

    def get_status_summary(self) -> dict:
        """Returns key pool health metadata without exposing actual keys."""
        now = time.time()
        return {
            "total_configured_keys": len(self.keys),
            "active_keys_count": sum(1 for i in range(len(self.keys)) if self.key_status.get(i, 0) <= now),
            "failing_keys_count": sum(1 for i in range(len(self.keys)) if self.key_status.get(i, 0) > now)
        }

# Global singleton instance
key_manager = GeminiKeyManager()
