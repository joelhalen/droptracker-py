# api.py

from quart import Blueprint, jsonify, render_template

# Create a Blueprint object
front = Blueprint('frontend', __name__)

@front.route('/')
async def homepage():
    return await render_template("index.html", page_name="Home")
    

@front.route('/info')
async def get_info():
    # Logic for another route
    return jsonify({"info": "This is some information!"})
