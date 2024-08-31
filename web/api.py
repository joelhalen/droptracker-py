# api.py

from quart import Blueprint, jsonify, request

from utils.redis import RedisClient

# Create a Blueprint object
api_blueprint = Blueprint('api', __name__)
redis_client = RedisClient()

@api_blueprint.route('/')
async def get_data():
    # Logic to retrieve or process data
    return jsonify({"message": "Hi there."})

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

@api_blueprint.route('/info')
async def get_info():
    # Logic for another route
    return jsonify({"info": "This is some information!"})
