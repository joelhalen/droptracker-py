from db.models import User, Group, Guild, Player, Drop, session
from dotenv import load_dotenv
import os
import asyncio
from datetime import datetime
from utils.redis import RedisClient

load_dotenv()

insertion = asyncio.Lock()

MAX_DROP_QUEUE_LENGTH = os.getenv("QUEUE_LENGTH")

redis_client = RedisClient()

class DatabaseOperations:
    def __init__(self) -> None:
        self.drop_queue = []
        pass

    async def add_drop_to_queue(self, drop_data: Drop):
        self.drop_queue.append(drop_data)
        if (len(self.drop_queue) > MAX_DROP_QUEUE_LENGTH):
            await self.insert_drops()
        
    async def insert_drops(self):
        async with insertion.Lock():
            length = len(self.drop_queue)
            for drop in self.drop_queue:
                try:
                    session.add(drop)
                except Exception as e:
                    print("Couldn't add a drop to the insertion list:", e)
                finally:
                    session.commit()
                    session.close()
                    self.drop_queue = []
        print("Inserted", length, "drops")
        
    def create_drop_object(self, item_name, item_id, player_id, date_received, value, quantity, add_to_queue: bool = True):
        """ Create a drop and add it to the queue for inserting to the database """
        newdrop = Drop(item_name = item_name,
                    item_id = item_id,
                    player_id = player_id,
                    date_received = date_received,
                    date_updated = date_received,
                    value = value,
                    quantity = quantity)
        if add_to_queue:
            self.add_drop_to_queue(newdrop)

    async def create_user(self, discord_id: str, username: str, ctx = None):
        """ 
            Creates a new 'user' in the database
        """
        new_user = User(discord_id=str(discord_id), username=str(username))
        try:
            session.add(new_user)
            session.commit()
            if ctx:
                await ctx.send(f"Your Discord account has been successfully registered in the DropTracker database!\n" +
                                "You must now use `/claim-rsn` in order to claim ownership of your accounts.")
            redis_client.set_discord_id_to_dt_id(discord_id=str(ctx.user.id),
                                                droptracker_id=str(new_user.user_id))
            return new_user
        except Exception as e:
            session.rollback()
            if ctx:
                await ctx.send(f"`You don't have a valid account registered, " +
                            "and an error occurred trying to create one. \n" +
                            "Try again later, perhaps.`", ephemeral=True)
            return None

    async def assign_rsn(user: User, player: Player):
        """ 
        :param: user: User object
        :param: player: Player object
            Assigns a 'player' to the specified 'user' object in the database
            :return: True/False if successful 
        """
        try:
            if not player.wom_id:
                return
            if player.user and player.user != user:
                """ 
                    Only allow the change if the player isn't already claimed.
                """
                return False
            else:
                player.user = user
                session.commit()
        except Exception as e:
            session.rollback()
            return False
        finally:
            return True

    async def find_drops_for_group(group_id: int = None, 
                               group_discord_id: str = None,
                               partition: int = None):
        if not group_id and not group_discord_id:
            return None
        elif group_discord_id and not group_id:
            group_id = redis_client.get(f"group:{group_discord_id}:dt_id")
        if group_id:
            if partition is None:
                partition = datetime.now().year * 100 + datetime.now().month
            
            all_drops = session.query(Drop.item_name, 
                                      Drop.item_id, 
                                      Drop.player,
                                      Drop.value,
                                      Drop.quantity,
                                      Drop.date_received
                                      ).filter(
                Drop.group_id == group_id,
                Drop.partition == partition
            ).all()
            
            return all_drops
        else:
            return None

    async def find_drops_for_player(player: Player,
                                    partition: int = None):
        if partition is None:
            partition = datetime.now().year * 100 + datetime.now().month
        player_drops = session.query(Drop.item_name,
                                     Drop.item_id,
                                     Drop.value,
                                     Drop.quantity,
                                     Drop.date_received,
                                     Drop.npc_name).filter(
                                         Drop.player == player).all()
        return player_drops