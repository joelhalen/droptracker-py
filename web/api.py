# api.py

from quart import Blueprint, jsonify

# Create a Blueprint object
api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/')
async def get_data():
    # Logic to retrieve or process data
    return jsonify({"message": "Hi there."})

@api_blueprint.route('/info')
async def get_info():
    # Logic for another route
    return jsonify({"info": "This is some information!"})
