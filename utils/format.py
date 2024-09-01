import time
from datetime import datetime

def format_time_since_update(datetime_object):
    # Convert the DateTime object to a Unix timestamp
    if datetime_object:
        unix_timestamp = int(datetime_object.timestamp())
    else:
        unix_timestamp = int(time.time())  # Default to current time if date_updated is None

    # Format the timestamp for Discord
    return f"<t:{unix_timestamp}:R>"

def format_number(): ## return a human readable format, like 106.56K, etc
    pass


def get_current_partition():
    now = datetime.now()
    return now.year * 100 + now.month

def normalize_npc_name(npc_name: str):
    return npc_name.replace(" ", "_").strip()
