import sys
import os
import json
import re
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from db.models import Player, Base  # Import Base using an absolute path

# Step 1: Read and Parse the SQL File
sql_file_path = '/store/tempdb/rsaccounts.sql'

with open(sql_file_path, 'r') as file:
    sql_content = file.read()

# Extracting INSERT data from the SQL file using regex
# Adjusted regex to match multi-line INSERT statements
insert_data_pattern = re.compile(r"INSERT INTO `rsaccounts` \(.*?\) VALUES\s*(.+?);", re.DOTALL)
matches = insert_data_pattern.findall(sql_content)

players_data = []

# Parse the matched INSERT statements to extract tuples of data
for match in matches:
    # Extract individual tuples
    data_tuples = re.findall(r"\((.*?)\)", match, re.DOTALL)
    for data_tuple in data_tuples:
        # Split by comma, but only outside of parenthesis to handle commas inside values
        values = [v.strip().strip("'") for v in data_tuple.split(",")]
        if len(values) == 4:
            player_id, display_name, wom_id, user_id = values
            players_data.append((int(player_id), display_name, int(wom_id), int(user_id) if user_id != 'NULL' else None))


# Step 2: Setup SQLAlchemy Session
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASS}@localhost:3306/data')  
Session = sessionmaker(bind=engine)
session = Session()

# Step 3: Check for Existing Players and Insert New Ones
for player_id, display_name, wom_id, user_id in players_data:
    # Check if a player with the same display name already exists (case-insensitive)
    existing_player = session.query(Player).filter(
        func.lower(Player.player_name) == display_name.lower()).first()
    if not existing_player:
        existing_player = session.query(Player).filter(Player.wom_id == wom_id).first()
    if not existing_player:
        # If the player does not exist, create a new Player object and add it to the session
        new_player = Player(
            wom_id=wom_id,
            player_name=display_name,
            user_id=user_id
        )
        session.add(new_player)
        print(f"Added new player: {display_name} with WOM ID: {wom_id}")

# Step 4: Commit the Session
try:
    session.commit()
    print("All new players have been successfully added to the database.")
except Exception as e:
    session.rollback()
    print(f"An error occurred: {e}")

# Step 5: Close the Session
session.close()


