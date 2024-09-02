from utils.redis import RedisClient
from db.models import User, Group, Guild, Player, Drop, session
from typing import List
from datetime import datetime
from datetime import timedelta

""" 
    This class attempts to store serialized versions of drop results in redis cache 
    to prevent the overhead of querying the database so frequently and serve data 
    more efficiently on scale
"""

"""
    Redis defs:
    -- Note: Stored without the {} brackets, ofc.
    - Player drop keys:
        Monthly:
            All:
                pid_drops_mo_{pid}_all_{partition}
            Specific NPC:
                pid_drops_mo_{pid}_{npc_name}_{partition}
        All-time (patreon):
            All:
                pid_drops_at_{pid}_all
            Specific NPC:
                pid_drops_at_{pid}_{npc_name}
    - Group drop keys:
        Monthly:
            All:
                gid_drops_mo_{gid}_all_{partition}
            Specific NPC:
                gid_drops_mo_{gid}_{npc_name}_{partition}
        All-time (patreon):
            All:
                gid_drops_at_{pid}_all
            Specific NPC:
                gid_drops_at_{pid}_{npc_name}
"""

redis_client = RedisClient()

# if drop.player and drop.player.user:
#     player: Player = drop.player
#     user: User = player.user
#     if user.patreon == True: 
#         player_totals[drop.player_id]["t"] = 5
class DropManager:
    def __init__(self) -> None:
        self.lock_key = "global_cache_last_run"
        self.lock_expiration = timedelta(minutes=30)
        pass

    def can_run(self) -> bool:
        """Check if the function can run based on the last run timestamp."""
        last_run_str = redis_client.get(self.lock_key)
        if last_run_str:
            last_run = datetime.fromisoformat(last_run_str)
            return datetime.now() - last_run >= self.lock_expiration
        return True
    
    def update_last_run(self) -> None:
        """Update the last run timestamp."""
        redis_client.set(self.lock_key, datetime.now().isoformat())

    def store_global_drops_to_redis(self, all_drops: List[Drop]):
        """
            REDIS
            Sorts drops and stores accumulated totals in the Redis cache.
            Only allowed to run every 30 minutes
        """
        if not self.can_run():
            return
        player_totals = {}
        group_totals = {}
        partition = datetime.now().year * 100 + datetime.now().month
        print(f"Processing {len(all_drops)} drops...")
        
        # Aggregate drops for players and groups
        for drop in all_drops:
            # Initialize player totals if not already present
            if drop.player_id not in player_totals:
                player_totals[drop.player_id] = {"all": 0}
            # Initialize NPC-specific drop totals for player
            if drop.npc_name not in player_totals[drop.player_id]:
                player_totals[drop.player_id][drop.npc_name] = 0
            
            entry_value = int(drop.value) * int(drop.quantity)
            player_totals[drop.player_id]["all"] += entry_value
            player_totals[drop.player_id][drop.npc_name] += entry_value
            
            # Aggregate group drops if group_id is present
            if drop.group_id:
                if drop.group_id not in group_totals:
                    group_totals[drop.group_id] = {"all": 0}
                if drop.npc_name not in group_totals[drop.group_id]:
                    group_totals[drop.group_id][drop.npc_name] = 0
                
                group_totals[drop.group_id]["all"] += entry_value
                group_totals[drop.group_id][drop.npc_name] += entry_value
        
        # Set player totals in Redis
        for player_id, totals in player_totals.items():
            for npc_name, total_value in totals.items():
                redis_client.set_pid_drops(
                    player_id=player_id,
                    total_value=total_value,
                    npc_name=npc_name,
                    partition=partition
                )
        
        # Set group totals in Redis
        for group_id, totals in group_totals.items():
            for npc_name, total_value in totals.items():
                redis_client.set_gid_drops(
                    group_id=group_id,
                    total_value=total_value,
                    npc_name=npc_name,
                    partition=partition
                )
        
        print("Player and group drops have been updated.")
                    


    def sort_all_drops(all_drops: List[Drop]):
        """ Sorts drops and stores the resulting data in the database, updating any past entries"""
        for drop in all_drops:
            pass