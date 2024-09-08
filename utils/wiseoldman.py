import os
import asyncio
import httpx
from asynciolimiter import Limiter
from dotenv import load_dotenv
from db.models import Player, session
import wom

load_dotenv()

rate_limit = 100 / 65  # This calculates the rate as 100 requests per 65 seconds
limiter = Limiter(rate_limit)  # Create a Limiter instance

# Fetch the WOM_API_KEY from environment variables
WOM_API_KEY = os.getenv("WOM_API_KEY")

# Initialize the WOM Client with API key and user agent
client = wom.Client(
    WOM_API_KEY,
    user_agent="@joelhalen"
)

async def check_user_by_username(username: str):
    """ Check a user in the WiseOldMan database, returning their "player" object,
        their WOM ID, and their displayName.
    """
    # TODO -- only grab necessary info and parse it before returning the full player obj?
    await client.start()  # Initialize the client (if required by the `wom` library)

    try:
        await limiter.wait()
        result = await client.players.get_details(username=username)
        if result.is_ok:
            player = result.unwrap()
            player_id = player.id
            player_name = player.username
            ## Return string types to ensure proper data storage in sql
            return player, str(player_name), str(player_id)
        else:
            result = await client.players.update_player(username=username)
            if result.is_ok:
                player = result.unwrap()
                player_id = player.id
                player_name = player.username
                ## Return string types to ensure proper data storage in sql
                return player, str(player_name), str(player_id)
            else:
                return None, None, None
    except Exception as e:
        print(f"Error while fetching user by username: {e}")
        return None, None, None

async def check_user_by_id(uid: int):
    """ Check a user in the WiseOldMan database, returning their "player" object,
        their WOM ID, and their displayName.
    """
    await client.start()  # Initialize the client (if required by the `wom` library)

    await limiter.wait()

    try:
        result = await client.players.get_details(id=uid)
        if result.is_ok:
            player = result.unwrap()
            player_id = player.player.id
            player_name = player.player.display_name
            return player, str(player_name), str(player_id)
        else:
            # Handle the case where the request failed
            return None, None, None
    finally:
        await client.close()

async def check_group_by_id(wom_group_id: int):
    """ Searches for a group on WiseOldMan by a passed group ID 
        Returns group_name, member_count and members (list)    
    """
    wom_id = str(wom_group_id)
    await client.start()
    await limiter.wait()
    try:
        result = await client.groups.get_details(id=wom_id)
        if result.is_ok:
            details = result.unwrap()
            members = details.memberships
            member_count = details.group.member_count
            group_name = details.group.name
            return group_name, member_count, members
        else:
            return None, None, None
    finally:
        await client.close()

async def fetch_group_members(wom_group_id: int):
    """ 
    Returns a list of WiseOldMan Player IDs 
    for members of a specified group 
    """
    user_list = []
    
    if wom_group_id == 1:
        # Fetch all player WOM IDs from the database directly
        players = session.query(Player.wom_id).all()
        # Unpack the list of tuples returned by SQLAlchemy
        user_list = [player.wom_id for player in players] 
        return user_list
    await client.start()
    await limiter.wait()
    try:
        result = await client.groups.get_details(wom_group_id)
        if result.is_ok:
            details = result.unwrap()
            members = details.memberships
            for member in members:
                user_list.append(member.player_id)
            return user_list
        else:
            return []
    finally:
        await client.close()
