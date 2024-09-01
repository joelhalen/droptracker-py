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

    def get_pid_drops(self, 
                  player_id: int, 
                  npc_name: str = None, 
                  partition: int = datetime.now().year * 100 + datetime.now().month) -> Optional[str]:
        """ 
            Retrieves drop totals for a player, optionally filtered by NPC and partition.
            A partition of 1 refers to all-time drops (patreon feature).
        """
        # Normalize the NPC name, defaulting to "all" if not provided
        if npc_name:
            npc_name = normalize_npc_name(npc_name)
        else:
            npc_name = "all"
        # Determine the key based on the partition
        if partition == 1:
            key = f"pid_drops_at_{player_id}_{npc_name}"
        else:
            key = f"pid_drops_mo_{player_id}_{npc_name}_{partition}"
        try:
            value = self.client.get(key)
            return value.decode('utf-8') if value else None
        except redis.RedisError as e:
            print(f"Error getting key '{key}': {e}")
            return None
        
    def set_pid_drops(self, 
                      player_id: int, 
                      total_value: int,
                      npc_name: str = None, 
                      partition: int = datetime.now().year * 100 + datetime.now().month):
        """ A partition of 1 refers to all-time drops (patreon feature) """
        if npc_name:
            npc_name = normalize_npc_name(npc_name)
        else:
            npc_name = "all"
        if partition == 1:
            key = f"pid_drops_at_{player_id}_{npc_name}"
        else:
            key = f"pid_drops_mo_{player_id}_{npc_name}_{partition}"
        try:
            self.client.set(key, total_value)
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
    
    def exists(self, key: str) -> bool:
        try:
            return self.client.exists(key)
        except redis.RedisError as e:
            print(f"Error checking existence of key '{key}': {e}")
            return False