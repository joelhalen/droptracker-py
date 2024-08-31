# redis.py
import redis
from typing import Optional

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

    def set_discord_id_to_dt_id(self, discord_id: str, droptracker_id: str) -> None:
        """
        :param: discord_id: The user's Discord ID (string formatted)
        :param: droptracker_id: The user's DropTracker UID (string formatted)
            Store an association between a discord id and a DropTracker unique user ID
        """
        try:
            self.client.set(f"uid_disc_{discord_id}", f"{droptracker_id}")
        except redis.RedisError as e:
            print("Error setting discord ID relation:", e)

    def find_dt_id_from_discord_id(self, discord_id: any) -> None:
        key = f"uid_disc_{discord_id}"
        try:
            value = self.client.get(key)
            return value.decode('utf-8') if value else None
        except redis.RedisError as e:
            print(f"Error getting UID from key '{key}':", e)

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
    
    def exists(self, key: str) -> bool:
        try:
            return self.client.exists(key)
        except redis.RedisError as e:
            print(f"Error checking existence of key '{key}': {e}")
            return False