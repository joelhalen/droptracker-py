import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, not_
from sqlalchemy.orm import sessionmaker
import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from db.models import Drop, NpcList  # Import necessary models

# Step 1: Set up database connection
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASS}@localhost:3306/data')
Session = sessionmaker(bind=engine)
session = Session()

sql_file_path = '/store/tempdb/dttransfer.sql'

with open(sql_file_path, 'r') as file:
    sql_content = file.read()

# Extracting INSERT data from the SQL file using regex
insert_data_pattern = re.compile(r"INSERT INTO `drops` \(.*?\) VALUES\s*(.+?);", re.DOTALL)
matches = insert_data_pattern.findall(sql_content)

drops_data = []
npc_drop_amounts = {}
# Parse the matched INSERT statements to extract tuples of data
for match in matches:
    data_tuples = re.findall(r"\((.*?)\)", match, re.DOTALL)
    for data_tuple in data_tuples:
        values = [v.strip().strip("'") for v in data_tuple.split(",")]
        if len(values) == 11:  # Ensure there are 11 fields
            drop_id, item_name, item_id, rsn, quantity, value, time_str, notified, image_url, npc_name, ym_partition = values
            normalized_npc_name = npc_name.replace("\\'", "'")
            if normalized_npc_name not in npc_drop_amounts:
                npc_drop_amounts[normalized_npc_name] = 1
            else:
                npc_drop_amounts[normalized_npc_name] += 1
            drops_data.append((int(drop_id), item_name, int(item_id), rsn, int(quantity), int(value), time_str, notified, image_url, npc_name, int(ym_partition)))

# Step 3: Keep track of rejected NPCs (both user-rejected and invalid ones from the URL check)
invalid_npcs = set()

# Step 4: Process all drops
print("Found all drops")
total_npcs = 0
sql_drops = session.query(Drop).all()

for drop in drops_data:
    normalized_npc_name = drop[9].replace("\\'", "'")  # Updated to use correct index for npc_name
    
    # Skip the NPC if it was previously rejected by the user or found to be invalid
    if normalized_npc_name in invalid_npcs:
        continue
    
    # Check if the NPC exists in the database
    npc = session.query(NpcList).filter_by(npc_name=normalized_npc_name).first()
    
    if not npc:
        print(f"NPC '{normalized_npc_name}' not found in the database.")
            # NPC exists, ask the user if they want to add it
        npc_counted = npc_drop_amounts[normalized_npc_name]
        print("Found", npc_counted, "drops for the npc")
        if npc_counted < 50:

            # user_input = input(f"NPC '{normalized_npc_name}' not found in the database. There are only {npc_counted} entries for this NPC name.\n " + 
            #                    "Do you want to add it to the database? (y/n): ").strip().lower()
        
            # if user_input == 'n':
            #     print(f"NPC '{normalized_npc_name}' will not be added and I won't ask again.")
            print("Skipping", normalized_npc_name, "because it only has", npc_counted)
            invalid_npcs.add(normalized_npc_name)
            continue
        print(f"[{npc_counted}] Adding NPC '{normalized_npc_name}' to the database...")
        try:
            new_npc = NpcList(npc_name=normalized_npc_name)
            session.add(new_npc)
            total_npcs += 1
        except Exception as e:
            print(f"Error adding NPC '{normalized_npc_name}': {e}")
    else:
        # NPC doesn't exist in the database
        print("Skipped", normalized_npc_name)
        invalid_npcs.add(normalized_npc_name)

# Step 6: Commit changes after all additions
try:
    session.commit()
    print(f"Data migration completed successfully. Added {total_npcs} NPCs.")
except Exception as e:
    session.rollback()
    print(f"An error occurred during data migration: {e}")

# Step 7: Close the session
session.close()

# Optional: Save invalid_npcs list to a file if you want persistence across runs
with open('invalid_npcs.txt', 'w') as f:
    for npc in invalid_npcs:
        f.write(f"{npc}\n")