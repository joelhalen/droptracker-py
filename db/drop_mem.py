from utils.redis import RedisClient
from db.models import User, Group, Guild, Player, Drop, session
from typing import List

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

class DropManager:
    def __init__(self) -> None:
        pass

    def sort_all_drops(all_drops: List[Drop]):
        """ Sorts drops and stores the resulting data in the database, updating any past entries"""
        for drop in all_drops:
            pass