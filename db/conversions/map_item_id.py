from sqlalchemy import create_engine, not_
from sqlalchemy.orm import sessionmaker
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from db.models import Drop, ItemList  # Import necessary models

# Step 1: Set up database connection
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASS}@localhost:3306/data')
Session = sessionmaker(bind=engine)
session = Session()

# Step 2: Fetch all item_ids from the ItemList table
item_ids = session.query(ItemList.item_id).all()
item_ids = [item_id[0] for item_id in item_ids]  # Flatten the list of tuples

# Step 3: Fetch all Drops where item_id is not in the list of existing item_ids
drops = session.query(Drop).filter(not_(Drop.item_id.in_(item_ids))).all()

for drop in drops:
    # Unescape apostrophes before querying
    normalized_item_name = drop.item_name.replace("\\'", "'")
    
    # Fetch the corresponding item_id from the ItemList table using normalized item_name
    item = session.query(ItemList).filter_by(item_name=normalized_item_name).first()
    
    if item:
        drop.item_id = item.item_id  # Assign the foreign key based on item_name
    else:
        new_item = ItemList(item_id=drop.item_id, item_name=drop.item_name, noted=False)
        print(f"Warning: No matching item found for item_name {drop.item_name}")
        print(f"Created a new entry with item ID #", drop.item_id)
        session.add(new_item)
try:
    session.commit()  # Commit the changes
    print("Data migration completed successfully.")
except Exception as e:
    session.rollback()
    print(f"An error occurred during data migration: {e}")

# Step 6: Close the session
session.close()
