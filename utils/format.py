import time
from datetime import datetime
import interactions

def format_time_since_update(datetime_object):
    """ 
        Returns a discord-formatted timestamp like '15 seconds ago' or 'in 3 days',
        which is non-timezone-specific.
    """
    # Convert the DateTime object to a Unix timestamp
    if datetime_object:
        unix_timestamp = int(datetime_object.timestamp())
    else:
        unix_timestamp = int(time.time())  # Default to current time if date_updated is None

    # Format the timestamp for Discord
    return f"<t:{unix_timestamp}:R>"

def format_number(): ## return a human readable format, like 106.56K, etc
    pass


def get_current_partition() -> int:
    """
        Returns the naming scheme for a partition of drops
        Based on the current month
    """
    now = datetime.now()
    return now.year * 100 + now.month

def normalize_npc_name(npc_name: str):
    return npc_name.replace(" ", "_").strip()


async def get_command_id(bot: interactions.Client, command_name: str):
    """
        Attempts to return the Discord ID for the passed 
        command name based on the context of the bot being used,
        incase the client is changed which would result in new command IDs
    """
    try:
        commands = bot.application_commands
        if commands:
            for command in commands:
                cmd_name = command.get_localised_name("en")
                print("Localized name:", cmd_name)
                if cmd_name == command_name:
                    print("Found matching command", command)
                    print("Returning ID", command.cmd_id[0])
                    return command.cmd_id[0]
        return "`command not yet added`"
    except Exception as e:
        print("Couldn't retrieve the ID for the command")
        print("Exception:", e)