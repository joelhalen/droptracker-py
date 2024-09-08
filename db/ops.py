from db.models import User, Group, Guild, Player, Drop, session, ItemList
from dotenv import load_dotenv
from sqlalchemy.dialects import mysql
import os
import asyncio
from datetime import datetime
from utils.redis import RedisClient
import pymysql

load_dotenv()

insertion_lock = asyncio.Lock()

MAX_DROP_QUEUE_LENGTH = os.getenv("QUEUE_LENGTH")

redis_client = RedisClient()

class DatabaseOperations:
    def __init__(self) -> None:
        self.drop_queue = []
        pass

    async def add_drop_to_queue(self, drop_data: Drop):
        self.drop_queue.append(drop_data)
        if (len(self.drop_queue) > int(MAX_DROP_QUEUE_LENGTH)):
            await self.insert_drops()
        
    async def insert_drops(self):
        async with insertion_lock:
            length = len(self.drop_queue)
            for drop in self.drop_queue:
                try:
                    session.add(drop)
                except Exception as e:
                    print("Couldn't add a drop to the insertion list:", e)
                    session.rollback()
                finally:
                    session.commit()
                    session.close()
                    self.drop_queue = []
        print("Inserted", length, "drops")
        
    async def create_drop_object(self, item_id, player_id, date_received, npc_id, value, quantity, add_to_queue: bool = True):
        """ :param: item_id: The item id that was received
            :param: player_id: The player's ID who received the drop
            :param: date_received: The current time / or when the drop was supposed to be inserted
            :param: npc_id: The ID of the NPC the drop was received from (based on our database of npc ids)
            :param: value: The item's GE value
            :param: quantity: How many of the item were received
            :param: add_to_queue: SETTING FALSE IGNORES ADDING THE DROP TO THE DATABASE...
            Create a drop and add it to the queue for inserting to the database """
        if isinstance(date_received, datetime):
            # Convert to string in the required format without timezone and microseconds
            date_received_str = date_received.strftime('%Y-%m-%d %H:%M:%S')
        else:
            date_received_str = date_received  # Assuming it's already a string in the correct format


        newdrop = Drop(item_id = item_id,
                    player_id = player_id,
                    date_added = date_received_str,
                    date_updated = date_received_str,
                    npc_id = npc_id,
                    value = value,
                    quantity = quantity)
        if add_to_queue:
            await self.add_drop_to_queue(newdrop)

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
        

    
        
    async def lootboard_drops(self):
        partition = datetime.now().year * 100 + (datetime.now().month)
        query = session.query(
            Drop.item_id, 
            Drop.player,
            Drop.value,
            Drop.quantity,
            Drop.date_added,
        ).filter(
            Drop.partition == partition
        ).join(
            Player, Drop.player_id == Player.player_id
        )
        print("Partition", partition)
        
        # Compile the query to a string with parameters bound
        sql_query = query.statement.compile(dialect=mysql.dialect())
        
        print(sql_query)
        all_drops = session.query(Drop.item_id, 
                                    Drop.player_id,
                                    Drop.value,
                                    Drop.quantity,
                                    Drop.date_added
                                    ).filter(
            Drop.partition == partition
        ).join(
            Player, Drop.player_id == Player.player_id
        ).all()
        
        
        # print("All drops:", all_drops)
        return all_drops
    # return sql_query
        
    async def find_all_drops(self):
        """ 
            Used for the global server's lootboard generation & 
            only does this month's partition
        """
        partition = datetime.now().year * 100 + (datetime.now().month - 1)
        """ 
            Used for the global server's lootboard generation & 
            only does this month's partition
        """
        #partition = datetime.now().year * 100 + (datetime.now().month - 1)
    
        query = session.query(
            Drop.item_id, 
            Drop.player,
            Drop.value,
            Drop.quantity,
            Drop.date_added,
        ).filter(
            Drop.partition == partition
        ).join(
            Player, Drop.player_id == Player.player_id
        )
        
        # Compile the query to a string with parameters bound
        sql_query = query.statement.compile(dialect=mysql.dialect())
        
        print(sql_query)
    # return sql_query
        # all_drops = session.query(Drop.item_name, 
        #                             Drop.item_id, 
        #                             Drop.player,
        #                             Drop.value,
        #                             Drop.quantity,
        #                             Drop.date_added,
        #                             Drop.group_id
        #                             ).filter(
        #     Drop.partition == partition
        # ).join(
        #     Player, Drop.player_id == Player.player_id
        # ).all()
        
        
        #print("All drops:", all_drops)
        #return all_drops

    async def find_drops_for_group(self,
                                   group_id: int = None, 
                               group_discord_id: str = None,
                               partition: int = None):
        if not group_id and not group_discord_id:
            return None
        if group_id:
            if partition is None:
                partition = datetime.now().year * 100 + datetime.now().month
            group = session.query(Group).filter(Group.group_id == group_id).first()
            all_drops = session.query(Drop.item_name, 
                                      Drop.item_id, 
                                      Drop.player,
                                      Drop.value,
                                      Drop.quantity,
                                      Drop.date_added
                                      ).filter(
                Drop.group == group,
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
                                     Drop.date_added,
                                     Drop.npc_name).filter(
                                         Drop.player == player).all()
        return player_drops
    
