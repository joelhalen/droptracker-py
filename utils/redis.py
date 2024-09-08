# redis.py
import redis
from typing import Optional
from utils.format import normalize_npc_name
from datetime import datetime

## Singleton RedisClient class
class RedisClient:
    _instance: Optional['RedisClient'] = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        if not hasattr(self, 'client'):
            self.client = redis.Redis(host=host, port=port, db=db)
    
    def set(self, key: str, value: str) -> None:
        try:
            self.client.set(key, value)
        except redis.RedisError as e:
            print(f"Error setting key '{key}': {e}")

    def get(self, key: str) -> Optional[str]:
        try:
            value = self.client.get(key)
            return value.decode('utf-8') if value else None
        except redis.RedisError as e:
            print(f"Error getting key '{key}': {e}")
            return None

    def delete(self, key: str) -> None:
        try:
            self.client.delete(key)
        except redis.RedisError as e:
            print(f"Error deleting key '{key}': {e}")
    
    def decode_data(self, data):
        return {key.decode('utf-8'): value.decode('utf-8') for key, value in data.items()}

    def exists(self, key: str) -> bool:
        try:
            return self.client.exists(key)
        except redis.RedisError as e:
            print(f"Error checking existence of key '{key}': {e}")
            return False