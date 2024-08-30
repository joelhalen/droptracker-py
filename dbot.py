
from dotenv import load_dotenv
import interactions
import time
from interactions import Intents, user_context_menu, ContextMenuContext, Member, listen, Status, Task, IntervalTrigger, \
    ActivityType, ChannelType, slash_command, Embed, slash_option, OptionType, check, is_owner, \
    slash_default_member_permission, Permissions, SlashContext, ButtonStyle, Button, SlashCommand, ComponentContext, \
    component_callback, Modal, ShortText, BaseContext
import os
load_dotenv()

class DiscordBot:
    def __init__(self, bot):
        self.bot = bot ## Passed instance of the created Discord bot
        self.login_time = int(time.time()) ## The time the bot connected for this session
        self.last_ping = int(time.time()) ## The last time the bot has received a valid request


