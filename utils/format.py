import time

def format_time_since_update(date_updated):
    # Convert the DateTime object to a Unix timestamp
    if date_updated:
        unix_timestamp = int(date_updated.timestamp())
    else:
        unix_timestamp = int(time.time())  # Default to current time if date_updated is None

    # Format the timestamp for Discord
    return f"<t:{unix_timestamp}:R>"

def format_number(): ## return a human readable format, like 106.56K, etc
    pass