import sys
import os
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from db.models import ItemList  # Import only the necessary models

# Step 1: Read and Parse the SQL File
sql_file_path = '/store/tempdb/dttransfer.sql'

with open(sql_file_path, 'r') as file:
    sql_content = file.read()

# Extracting INSERT data from the SQL file using regex
insert_data_pattern = re.compile(r"INSERT INTO `drops` \(.*?\) VALUES\s*(.+?);", re.DOTALL)
matches = insert_data_pattern.findall(sql_content)

item_list = {}
total_len = 0
# Parse the matched INSERT statements to extract tuples of data
for match in matches:
    data_tuples = re.findall(r"\((.*?)\)", match, re.DOTALL)
    for data_tuple in data_tuples:
        total_len += 1
        # Split by comma, but only outside of parenthesis to handle commas inside values
        values = [v.strip().strip("'") for v in data_tuple.split(",")]
        if len(values) == 11:  # Ensure there are 11 fields
            drop_id, item_name, item_id, rsn, quantity, value, time_str, notified, image_url, npc_name, ym_partition = values
            item_id = int(item_id)  # Convert item_id to integer
            if item_id not in item_list:
                item_list[item_id] = item_name
print(f"Found {len(item_list)} items in the database based on {total_len} drops")
print("Adding them to the ItemList table")

# Step 2: Connect to the database
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASS}@localhost:3306/data')  
Session = sessionmaker(bind=engine)
session = Session()

# Fetch existing items from the database
existing_items = {item.item_id for item in session.query(ItemList.item_id).all()}

# Step 3: Add items to the database only if they don't already exist
new_entries = 0  # Count new entries added
for item_id, item_name in item_list.items():
    if item_id not in existing_items:
        new_item = ItemList(item_id=item_id, item_name=item_name, noted=False)
        session.add(new_item)
        new_entries += 1  # Increment count for new entries

try:
    session.commit()
    print(f"All drops have been successfully added to the database. {new_entries} new entries were inserted.")
except Exception as e:
    session.rollback()
    print(f"An error occurred: {e}")

# Step 6: Close the Session
session.close()
