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
from web.front import create_frontend
from web.oauth.discord_login import create_discord_oauth
from commands import UserCommands, ClanCommands, AdminCommands
from db.models import session, NpcList, ItemList
from db.update_player_total import start_background_redis_tasks
from utils.messages import message_processor

## global variables modified throughout operation + accessed elsewhere ##
total_guilds = 0
total_users = 0
start_time: time = None
current_time = time.time()

## Category IDs that contain DropTracker webhooks that receive messages from the RuneLite client

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
front = create_frontend(bot)
discord_oauth = create_discord_oauth(bot)

app.register_blueprint(api_blueprint, url_prefix='/api')
app.register_blueprint(front, url_prefix='/')
app.register_blueprint(discord_oauth, url_prefix='/')
app.secret_key = os.getenv('APP_SECRET_KEY')



@listen(Startup)
async def on_startup(event: Startup):
    global start_time
    start_time = time.time()
    global total_guilds
    print(f"Connected as {bot.user.display_name} with id {bot.user.id}")
    await bot.change_presence(status=interactions.Status.ONLINE,
                              activity=interactions.Activity(name=f" /help", type=interactions.ActivityType.WATCHING))
    bot.load_extension("commands")
    await create_tasks()
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
    await message_processor(bot, event)
    # if event.message.author.id == bot.user.id or event.message.system_content:
    #     return
    # if event.message.channel:
    #     if event.message.channel.parent_id:
    #         if event.message.webhook_id:
    #             #print("Message has a webhook ID")
    #             pass
    
@listen(Component)
async def on_component_use(event: Component):
    global ignored_list
    ctx = event.ctx

    if "confirm_npc_" in ctx.custom_id:
        npc_name = ctx.custom_id.replace("confirm_npc_", "")
        new_npc = NpcList(npc_name=npc_name)
        try:
            session.add(new_npc)
            session.commit()
            await ctx.send(f"Added {npc_name} with ID `{new_npc.npc_id}` to the database.")
        except Exception as e:
            await ctx.send(f"Couldn't add the NPC to the database:", e)
    elif f"deny_npc_" in ctx.custom_id:
        npc_name = ctx.custom_id.replace("deny_npc_", "")
        ignored_list.append(npc_name)
        await ctx.send(f"Npc ignored, won't ask again.")

    elif f"confirm_item_" in ctx.custom_id:
        stripped = ctx.custom_id.replace("confirm_item_", "")
        item_name, item_id = stripped.split("__")
        item_name.replace("__","").replace("_","").trim()
        item_id.replace("__","").replace("_","").trim()
        try:
            new_item = ItemList(item_id=item_id,
                                item_name=item_name,
                                noted=False)
            session.add(new_item)
            session.commit()
        except Exception as e:
            session.rollback()
            print("Failed to add a new item.")
            return await ctx.send(f"Failed to add the item:", e)
        
    
## Tasks
async def create_tasks():
    print("Starting the database sync tasks for Redis caching")
    await start_background_redis_tasks()

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
