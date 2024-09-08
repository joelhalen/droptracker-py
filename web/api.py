# api.py

from quart import Blueprint, jsonify, request
from db.models import User, Group, Guild, Player, Drop, session, ItemList
from concurrent.futures import ThreadPoolExecutor
from db.ops import DatabaseOperations
from db.update_player_total import update_player_totals
import asyncio
from datetime import datetime

from utils.redis import RedisClient
executor = ThreadPoolExecutor()

# Create a Blueprint object
api_blueprint = Blueprint('api', __name__)
redis_client = RedisClient()

@api_blueprint.route('/')
async def get_data():
    # Run the blocking function in a thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, update_player_totals)

    # Immediately return a response
    return jsonify({"message": "Started background task to update player totals."})


@api_blueprint.route('/player/<int:player_id>', methods=['GET'])
async def get_player_data(player_id):
    """
    Endpoint to get a player's data from Redis.
    :param player_id: Player ID to retrieve data for.
    :query param partition: Optional partition parameter (defaults to current partition if not provided).
    """
    # Get the partition from the query parameter or default to the current partition
    partition = request.args.get('partition', default=datetime.now().year * 100 + datetime.now().month, type=int)

    # Define Redis keys for this player using the partition
    total_items_key_partition = f"player:{player_id}:{partition}:total_items"
    npc_totals_key_partition = f"player:{player_id}:{partition}:npc_totals"
    total_loot_key_partition = f"player:{player_id}:{partition}:total_loot"
    recent_items_key_partition = f"player:{player_id}:{partition}:recent_items"

    # Fetch data from Redis
    total_items = redis_client.client.hgetall(total_items_key_partition)
    npc_totals = redis_client.client.hgetall(npc_totals_key_partition)
    total_loot = redis_client.get(total_loot_key_partition)
    recent_items = redis_client.client.lrange(recent_items_key_partition, 0, -1)  # Get all recent items

    # Extract the data from bytes format
    total_items = redis_client.decode_data(total_items)
    npc_totals = redis_client.decode_data(npc_totals)
    recent_items = [item.decode('utf-8') for item in recent_items]

    # Return the data in JSON format
    return jsonify({
        "total_items": total_items,
        "npc_totals": npc_totals,
        "total_loot": total_loot,
        "recent_items": recent_items
    })

@api_blueprint.route('/players', methods=['GET'])
async def get_all_players_data():
    """
    Endpoint to get data for players from Redis.
    Accepts query parameters for pagination and returns up to 50 players by default.
    If 'all=true' is passed, returns data for all players.
    Accepts optional 'partition' query parameter, defaults to the current partition.
    """
    # Get the partition from the query parameter or default to the current partition
    partition = request.args.get('partition', default=datetime.now().year * 100 + datetime.now().month)

    # Get query parameters for pagination
    start_id = request.args.get('start_id', type=int, default=0)
    limit = request.args.get('limit', type=int, default=50)
    return_all = request.args.get('all', type=bool, default=False)

    # Query for player IDs and names
    query = session.query(Player.player_id, Player.player_name)
    
    if start_id > 0:
        query = query.filter(Player.player_id >= start_id)
    
    if not return_all:
        query = query.limit(limit)

    player_data = query.all()

    players_data = {}

    for player_id, player_name in player_data:
        # Define Redis keys for this player using the partition
        total_items_key_partition = f"player:{player_id}:{partition}:total_items"
        npc_totals_key_partition = f"player:{player_id}:{partition}:npc_totals"
        total_loot_key_partition = f"player:{player_id}:{partition}:total_loot"
        recent_items_key_partition = f"player:{player_id}:{partition}:recent_items"

        # Fetch and decode data from Redis
        total_items = redis_client.decode_data(redis_client.client.hgetall(total_items_key_partition))
        npc_totals = redis_client.decode_data(redis_client.client.hgetall(npc_totals_key_partition))
        total_loot = redis_client.get(total_loot_key_partition)
        recent_items = [item.decode('utf-8') for item in redis_client.client.lrange(recent_items_key_partition, 0, -1)]

        # Add the player's data to the result
        players_data[player_id] = {
            "rsn": player_name,
            "total_items": total_items,
            "npc_totals": npc_totals,
            "total_loot": total_loot,
            "recent_items": recent_items
        }

    return jsonify(players_data)


@api_blueprint.route('/claim_rsn', methods=['POST'])
async def claim_rsn():
    """ 
        Claim an RSN as belonging to a specific Discord account
        Intended to prevent people maliciously claiming accounts that they do not own,
        uses a remedial authentication system to check if they submit a match for the claim
    """
    try:
        data = await request.get_json()
        rsn = data.get('rsn')
        token = data.get('token')
        
        if not rsn:
            return jsonify({'error': 'No RSN provided'}), 400
        data = redis_client.get(f'auth-{rsn}')
        if data.lower().strip() == token.lower().strip():
            ## The stored token matches the one they passed in the RuneLite command
            pass
        # return jsonify(response_data), 200

    except Exception as e:
        # Handle exceptions, possibly logging them
        return jsonify({'error': str(e)}), 500

@api_blueprint.route('/item-id', methods=['GET'])
async def get_info():
    item_name = request.args.get('name')
    noted_param = request.args.get('noted', 'false').lower()
    normalized_name = item_name.strip().lower() if item_name else None
    noted = True if noted_param == 'true' else False
    item = session.query(ItemList).filter(ItemList.item_name == normalized_name,
                                          ItemList.noted == noted).first()
    # Logic for another route
    if item:
        return jsonify({"item_name": normalized_name,
                        "item_id": item.item_id,
                        "noted": noted}), 200
    else:
        return jsonify({"error": f"Item '{normalized_name}' not found."}), 404
