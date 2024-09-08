# api.py

import interactions

from quart import Blueprint, jsonify, render_template, request, session as sesh
from db.ops import DatabaseOperations
from db.models import Group, GroupConfiguration, session as db_sesh, User, Guild

def create_frontend(bot: interactions.Client):
# Create a Blueprint object
    front = Blueprint('frontend', __name__)

    db = DatabaseOperations()

    @front.route('/')
    async def homepage():
        return await render_template("index.html", page_name="Home")
        
    @front.route('/group-settings', methods=["GET", "POST"])
    async def group_config_page():
        user = sesh.get('user', None)
        if not user:
            return await render_template('index.html')
        if request.method == "POST":
            ## TODO - handle config change
            pass
        else:
            dt_user = db_sesh.query(User).filter(User.discord_id == user['id']).first()
            if not dt_user:
                ## TODO -- you are not logged in page
                return await render_template('index.html')
            else:
                groups = dt_user.groups
                if groups:
                    # Extract the DropTracker groupIDs
                    group_data = []
                    for group in groups:
                        group_data.append({
                            'group_id': group.group_id,
                        })
                    if len(group_data) > 1:
                        print("User has > 1 group")
                        # TODO - ask which group to edit
                        pass
                    group_id = group_data[0]['group_id']
                    print("Using group_id", group_id)
                    group_config = db_sesh.query(GroupConfiguration).filter(GroupConfiguration.group_id == group_id).all()
                    print("Group config:", group_config)
                    # Transform group_config into a dictionary for easy access
                    config = {conf.config_key: conf.config_value for conf in group_config}
                    guild: Guild = db_sesh.query(Guild).filter(Guild.group_id == group.group_id).first()
                    if not guild:
                        print("No guild found for group id", group_id)
                        return ## do something ?
                    guild_id = guild.guild_id
                    group_channels = []
                    discord_guild = await bot.fetch_guild(guild_id=guild_id)
                    channels = await discord_guild.fetch_channels()
                    for channel in channels:
                        #TODO - fix channel type detection (0 = text, but 1=voice must be wrong)
                        if channel.type == 0:
                            channel_type = "text"
                        elif channel.type == 1:
                            channel_type = "voice"
                        else:
                            continue
                        group_channels.append({"name": channel.name,
                                               "id": channel.id,
                                               "type": channel_type})
                    return await render_template('group/config.html', config=config,channel_list=group_channels)
                    return await render_template('group/config.html', group_config=group_config)
                else:
                    ## TODO - let them know they need to register group on Discord first
                    print("No user groups")
                    pass
        
            # return await render_template('group/config.html')

    @front.route('/info')
    async def get_info():
        # Logic for another route
        return jsonify({"info": "This is some information!"})
    

    return front