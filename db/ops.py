from db.models import User, Group, Guild, Player, Drop, session
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

insertion = asyncio.Lock()

MAX_DROP_QUEUE_LENGTH = os.getenv("QUEUE_LENGTH")

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
        newdrop = Drop(item_name = item_name,
                    item_id = item_id,
                    player_id = player_id,
                    date_received = date_received,
                    date_updated = date_received,
                    value = value,
                    quantity = quantity)
        if add_to_queue:
            self.add_drop_to_queue(newdrop)


