
import interactions
import json
from dotenv import load_dotenv
import asyncio
import os
from interactions import Intents, user_context_menu, ContextMenuContext, Member, listen, Status, Task, IntervalTrigger, \
    ActivityType, ChannelType, slash_command, Embed, slash_option, OptionType, check, is_owner, \
    slash_default_member_permission, Permissions, SlashContext, ButtonStyle, Button, SlashCommand, ComponentContext, \
    component_callback, Modal, ShortText, BaseContext
from interactions.api.events import GuildJoin, GuildLeft, MessageCreate, Component, Startup

bot = interactions.Client(intents=Intents.ALL)
from dbot import DiscordBot as dt ## Import the custom class for the bot object as 'dt'

load_dotenv()
bot_token = os.getenv('BOT_TOKEN')


@listen(Startup)
async def on_startup():
    print(f"Connected as {bot.user.display_name} with id {bot.user.id}")
    await bot.change_presence(status=interactions.Status.ONLINE,
                              activity=interactions.Activity(name=f" /help", type=interactions.ActivityType.WATCHING))

## Guild Events ##
@listen(GuildJoin)
async def joined_guild(event: GuildJoin):
    pass

@listen(GuildLeft)
async def left_guild(event: GuildLeft):
    pass

@listen(MessageCreate)
async def on_message_create():
    ## Handle webhook messages
    pass


if __name__ == '__main__':
    try:
        bot.start(token=bot_token)
        dt = dt(bot)
    except Exception as e:
        print("Bot crashed.", e)