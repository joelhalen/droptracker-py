import sys
import os
import json
import re
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from db.models import Player, Drop, Base  # Import Base using an absolute path

# Step 1: Read and Parse the SQL File
sql_file_path = '/store/tempdb/dttransfer.sql'

with open(sql_file_path, 'r') as file:
    sql_content = file.read()

# Extracting INSERT data from the SQL file using regex
# Adjusted regex to match multi-line INSERT statements
insert_data_pattern = re.compile(r"INSERT INTO `drops` \(.*?\) VALUES\s*(.+?);", re.DOTALL)
matches = insert_data_pattern.findall(sql_content)

drops_data = []

# Parse the matched INSERT statements to extract tuples of data
for match in matches:
    # Extract individual tuples
    data_tuples = re.findall(r"\((.*?)\)", match, re.DOTALL)
    for data_tuple in data_tuples:
        # Split by comma, but only outside of parenthesis to handle commas inside values
        values = [v.strip().strip("'") for v in data_tuple.split(",")]
        if len(values) == 11:  # Ensure there are 11 fields
            drop_id, item_name, item_id, rsn, quantity, value, time_str, notified, image_url, npc_name, ym_partition = values
            drops_data.append((int(drop_id), item_name, int(item_id), rsn, int(quantity), int(value), time_str, notified, image_url, npc_name, int(ym_partition)))


# Step 2: Setup SQLAlchemy Session
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASS}@localhost:3306/data')  
Session = sessionmaker(bind=engine)
session = Session()

# Step 3: Create a Cache for Player IDs
player_cache = {}

# Optional: Preload Cache with Existing Players (for large datasets)
players = session.query(Player).all()
for player in players:
    player_cache[player.player_name.lower()] = player.player_id

# Step 4: Process and Insert Drops
for drop_id, item_name, item_id, rsn, quantity, value, time_str, notified, image_url, npc_name, ym_partition in drops_data:
    # Check the cache for the player_id
    player_id = player_cache.get(rsn.lower())
    if not player_id:
        # If not found in cache, query the database
        player = session.query(Player).filter(func.lower(Player.player_name) == rsn.lower()).first()
        if player:
            player_id = player.player_id
            # Store in cache for future use
            player_cache[rsn.lower()] = player_id
        else:
            # If player not found, handle the case (e.g., log, skip, or create new player)
            print(f"Player {rsn} not found, skipping drop {drop_id}")
            continue

    # Create a new Drop object and add it to the session
    new_drop = Drop(
        drop_id=drop_id,
        item_name=item_name,
        item_id=item_id,
        player_id=player_id,
        quantity=quantity,
        value=value,
        date_added=datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S') if time_str != '0000-00-00 00:00:00' else None,
        date_updated=datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S') if time_str != '0000-00-00 00:00:00' else None,
        npc_name=npc_name,
        partition=ym_partition  # Or use appropriate partitioning logic
    )
    session.add(new_drop)
    print(f"Added drop {drop_id} for player {rsn}")

# Step 5: Commit the Session
try:
    session.commit()
    print("All drops have been successfully added to the database.")
except Exception as e:
    session.rollback()
    print(f"An error occurred: {e}")

# Step 6: Close the Session
session.close()