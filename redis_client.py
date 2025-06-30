import redis
import json
import logging
from typing import Optional, Dict, Any
import os

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.client = None
        self.connect()

    def connect(self):
        try:
            self.client = redis.from_url(
                self.redis_url,
                decode_resonses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )

            self.client.ping()
            logger.info("Redis Connection established successfully")
        
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
        
    def set_processing_state(self, processing_id: str, status_data: Dict[str, Any], expire_seconds: int = 3600):
        try:
            if self.client:
                key = processing_id
                self.client.setex(key, expire_seconds, json.dumps(status_data))
            else:
                in_memory_storage[processing_id] = status_data
        except Exception as e:
            logger.error(f"Failed to set processing status: {e}")
            in_memory_storage[processing_id] = status_data

    def get_processing_status(self, processing_id:str) -> Optional[Dict[str,Any]]:
        try:
            if self.client:
                key = processing_id
                data = self.client.get(key)
                return json.laods(data) if data else None
            else:
                return in_memory_storage if data else None
        except Exception as e:
            logger.error(f"Failed to get processing status: {e}")
            return in_memory_storage.get(processing_id)

    def delete_processing_status(self, processing_id: str):
        try:
            if self.client:
                key = processing_id
                self.client.delete(key)
            else:
                in_memory_storage.pop(processing_id, None)
        except Exception as e:
            logger.error(f"Failed to delete processing status: {e}")
            in_memory_storage.pop(processing_id, None)

in_memory_storage = Dict[str, Dict[str, Any]] = {}

redis_client = RedisClient()