import interactions
import json
from dotenv import load_dotenv
import asyncio
import os
import time
from quart import Quart, jsonify
import hypercorn.asyncio
from interactions import Intents, user_context_menu, ContextMenuContext, Member, listen, Status, Task, IntervalTrigger, \
    ActivityType, ChannelType, slash_command, Embed, slash_option, OptionType, check, is_owner, \
    slash_default_member_permission, Permissions, SlashContext, ButtonStyle, Button, SlashCommand, ComponentContext, \
    component_callback, Modal, ShortText, BaseContext, Extension
from interactions.api.events import GuildJoin, GuildLeft, MessageCreate, Component, Startup
from web.api import api_blueprint
from web.front import front
from commands import UserCommands, ClanCommands, AdminCommands
from db.models import session  # Import the database session

## global variables modified throughout operation + accessed elsewhere ##
total_guilds = 0
total_users = 0
start_time: time = None
current_time = time.time()

## Category IDs that contain DropTracker webhooks that receive messages from the RuneLite client
webhook_category_list = ["1211062421591167016"]

load_dotenv()
# Hypercorn configuration
def create_hypercorn_config():
    config = hypercorn.Config()
    config.bind = ["0.0.0.0:8080"]  # Bind to all interfaces on port 8080
    config.timeout = 60  # Timeout for connections
    return config

## Discord Bot initialization ##

bot = interactions.Client(intents=Intents.ALL)
bot_token = os.getenv('BOT_TOKEN')

## Quart server initialization ##
app = Quart(__name__)
app.register_blueprint(api_blueprint, url_prefix='/api')
app.register_blueprint(front, url_prefix='/')



@listen(Startup)
async def on_startup(event: Startup):
    global start_time
    start_time = time.time()
    global total_guilds
    print(f"Connected as {bot.user.display_name} with id {bot.user.id}")
    await bot.change_presence(status=interactions.Status.ONLINE,
                              activity=interactions.Activity(name=f" /help", type=interactions.ActivityType.WATCHING))
    bot.load_extension("commands")
    total_guilds = len(bot.guilds)


## Guild Events ##

@listen(GuildJoin)
async def joined_guild(event: GuildJoin):
    global total_guilds
    total_guilds += 1
    pass

@listen(GuildLeft)
async def left_guild(event: GuildLeft):
    global total_guilds
    total_guilds -= 1
    pass

## Message Events ##

@listen(MessageCreate)
async def on_message_create(event: MessageCreate):
    if event.message.author.id == bot.user.id or event.message.system_content:
        return
    if event.message.channel:
        if event.message.channel.parent_id:
            if event.message.webhook_id:
                #print("Message has a webhook ID")
                pass
    

## User Events ##

async def main():
    bot_task = asyncio.create_task(bot.astart(bot_token))
    # Run Quart server with Hypercorn
    hypercorn_config = create_hypercorn_config()
    quart_task = asyncio.create_task(
        hypercorn.asyncio.serve(app, hypercorn_config)
    )
    await asyncio.gather(bot_task, quart_task)


if __name__ == '__main__':
    asyncio.run(main())
