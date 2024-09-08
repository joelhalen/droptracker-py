import asyncio
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from db.models import Drop
from datetime import datetime
import json
import os
import concurrent.futures
from utils.redis import RedisClient
from interactions import Task, IntervalTrigger

# Initialize Redis
redis_client = RedisClient()

# Redis Keys
LAST_DROP_ID_KEY = "last_processed_drop_id"
MINIMUM_RECENT_VALUE = 2500000  # 2.5M minimum

# Batch size for pagination
BATCH_SIZE = 1000  # Number of drops processed at once

def get_last_processed_drop_id():
    return int(redis_client.get(LAST_DROP_ID_KEY) or 0)

def set_last_processed_drop_id(drop_id):
    redis_client.set(LAST_DROP_ID_KEY, drop_id)

def process_drops_batch(batch_drops):
    """
    Processes a batch of drops and updates Redis accordingly.
    This function can be run in parallel across multiple threads.
    """
    pipeline = redis_client.client.pipeline(transaction=False)

    for drop in batch_drops:
        player_id = drop.player_id
        npc_id = drop.npc_id
        item_id = drop.item_id
        partition = drop.partition  # Get the partition from the drop
        total_value = drop.value * drop.quantity

        # Create Redis keys for player and NPC-specific totals, partitioned and 'all'
        total_items_key_partition = f"player:{player_id}:{partition}:total_items"
        total_items_key_all = f"player:{player_id}:all:total_items"
        
        npc_totals_key_partition = f"player:{player_id}:{partition}:npc_totals"
        npc_totals_key_all = f"player:{player_id}:all:npc_totals"
        
        total_loot_key_partition = f"player:{player_id}:{partition}:total_loot"
        total_loot_key_all = f"player:{player_id}:all:total_loot"
        
        recent_items_key_partition = f"player:{player_id}:{partition}:recent_items"
        recent_items_key_all = f"player:{player_id}:all:recent_items"

        # Update total item count and value for both partition and 'all'
        item_data_partition = redis_client.client.hget(total_items_key_partition, item_id)
        item_data_all = redis_client.client.hget(total_items_key_all, item_id)

        if item_data_partition:
            existing_qty, existing_value = map(int, item_data_partition.split(','))
            new_qty = existing_qty + drop.quantity
            new_value = existing_value + total_value
        else:
            new_qty = drop.quantity
            new_value = total_value

        # Store item quantity and value as a string "quantity,value"
        pipeline.hset(total_items_key_partition, item_id, f"{new_qty},{new_value}")
        pipeline.hset(total_items_key_all, item_id, f"{new_qty},{new_value}")

        # Batch update cumulative total loot from NPCs
        pipeline.hincrby(npc_totals_key_partition, npc_id, total_value)
        pipeline.hincrby(npc_totals_key_all, npc_id, total_value)

        # Batch update overall total loot
        pipeline.incrby(total_loot_key_partition, total_value)
        pipeline.incrby(total_loot_key_all, total_value)

        # Check if this drop exceeds the MINIMUM_RECENT_VALUE for recent items
        if drop.value >= MINIMUM_RECENT_VALUE:
            recent_item_data = { 
                "item_id": item_id,
                "npc_id": npc_id,
                "player_id": player_id,
                "value": total_value,
                "date_added": drop.date_added.isoformat()
            }
            recent_item_json = json.dumps(recent_item_data)
            # Batch update recent items list in both partitions
            pipeline.rpush(recent_items_key_partition, recent_item_json)
            pipeline.rpush(recent_items_key_all, recent_item_json)

    # Execute the Redis pipeline batch
    pipeline.execute()



async def update_player_totals():
    """
    Function to update player totals by fetching new drop records
    from the database and updating the Redis cache.
    This function runs in the background to ensure the cache is up to date.
    """
    DB_USER = os.getenv('DB_USER')
    DB_PASS = os.getenv('DB_PASS')
    engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASS}@localhost:3306/data')
    Session = sessionmaker(bind=engine)
    session = Session()

    # Get the last drop_id processed
    last_drop_id = get_last_processed_drop_id()

    # Fetch all drop IDs after the last processed drop_id
    drop_count = session.query(func.count(Drop.drop_id)).filter(Drop.drop_id > last_drop_id).scalar()
    print(f"Starting at ID {last_drop_id}. Total drops left to process: {drop_count}")

    # Fetch drops after the last processed drop_id in batches
    offset = 0

    # Use ThreadPoolExecutor to process batches in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        processed_drops = 0
        while offset < drop_count:
            # Fetch the next batch of drops
            batch_drops = session.query(Drop).filter(Drop.drop_id > last_drop_id)\
                                             .order_by(Drop.drop_id.asc())\
                                             .limit(BATCH_SIZE)\
                                             .offset(offset)\
                                             .all()

            if not batch_drops:
                break  # Exit if no more drops

            last_batch_drop_id = batch_drops[-1].drop_id

            # Submit each batch to be processed by a separate thread
            futures.append(executor.submit(process_drops_batch, batch_drops))

            # Update the last processed drop ID
            set_last_processed_drop_id(last_batch_drop_id)

            # Increase the offset for the next batch
            offset += BATCH_SIZE

        # Wait for all threads to complete
        concurrent.futures.wait(futures)

    session.close()
    print("Drops processed successfully.")

async def background_task():
    """
    Background task that runs the update_player_totals function in a loop,
    ensuring the cache is updated periodically without stalling the main application.
    """
    while True:
        try:
            print("Updating drops...")
            await update_player_totals()
        except Exception as e:
            print(f"Error in update_player_totals: {e}")
        await asyncio.sleep(60)  # Wait for 60 seconds before the next run (adjust as needed)

# Add this to your Quart or Discord bot setup
async def start_background_redis_tasks():
    """
    Starts the background tasks for the Quart server or Discord bot.
    This ensures that update_player_totals runs without blocking the main event loop.
    """
    asyncio.create_task(background_task())
