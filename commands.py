from interactions import SlashCommand, Button, ButtonStyle, check, is_owner, Extension, slash_command, slash_option, SlashContext, Embed, OptionType
import interactions
import time
import subprocess
import platform
from db.models import User, Group, Guild, Player, Drop, session, GroupConfiguration
from utils.format import format_time_since_update, format_number, get_command_id
from utils.wiseoldman import check_user_by_id, check_user_by_username, check_group_by_id
from utils.redis import RedisClient
from db.ops import DatabaseOperations
from lootboard.generator import generate_server_board
from datetime import datetime
import asyncio


redis_client = RedisClient()
db = DatabaseOperations()

# Commands for the general user to interact with the bot
class UserCommands(Extension):
    @slash_command(name="help",
                   description="View helpful commands/links for the DropTracker")
    async def help(self, ctx):
        user = session.query(User).filter_by(discord_id=str(ctx.user.id)).first()
        if not user:
            await try_create_user(ctx)
        help_embed = Embed(title="", description="", color=0x0ff000)

        help_embed.set_author(name="Help Menu",
                              url="https://www.droptracker.io/docs",
                              icon_url="https://www.droptracker.io/img/droptracker-small.gif")
        help_embed.set_thumbnail(url="https://www.droptracker.io/img/droptracker-small.gif")
        help_embed.set_footer(text="View our documentation to learn more about how to interact with the Discord bot.")
        help_embed.add_field(name="Note:",
                            value=f"To register your Discord account, use any of the **user commands** for the first time")
        help_embed.add_field(name="User Commands:",
                             value="" +
                                   f"- </me:{await get_command_id(self.bot, 'me')}> - View your account / stats\n" + 
                                   f"- </user-config:{await get_command_id(self.bot, 'user-config')}> - Configure your user-specific settings, such as google sheets & webhooks.\n" +
                                   f"- </accounts:{await get_command_id(self.bot, 'accounts')}> - View which RuneScape accounts are associated with your Discord account.\n" +
                                   f"- </claim-rsn:{await get_command_id(self.bot, 'claim-rsn')}> - Claim a RuneScape character as one that belongs to you.\n"
                                   f"- </stats:{await get_command_id(self.bot, 'stats')}> - View general DropTracker statistics, or search for a player/clan.\n" +
                                   f"- </patreon:{await get_command_id(self.bot, 'patreon')}> - View the benefits of contributing to keeping the DropTracker online via Patreon.", inline=False)
        help_embed.add_field(name="Group Leader Commands:",
                             value="" +
                                   f"- <:info:1263916332685201501> </create-group:{await get_command_id(self.bot, 'create-group')}> - Create a new group in the DropTracker database to track your clan's drops.\n" +
                                   f"- </group:{await get_command_id(self.bot, 'group')}> - View relevant config options, member counts, etc.\n" +
                                   f"- </group-config:{await get_command_id(self.bot, 'group-config')}> - Begin configuring the DropTracker bot for use in a Discord server, with a step-by-step walkthrough.\n" +
                                   f"- </members:{await get_command_id(self.bot, 'members')}> - View a listing of the top members of your group in real-time.\n" +
                                   f"- </group-refresh:{await get_command_id(self.bot, 'group-refresh')}> - Request an instant refresh of the database for your group, if something appears missing\n" + 
                                   f"<:info:1263916332685201501> - **command requires ownership of the discord server you execute the command from inside of**", inline=False)
        if ctx.guild and ctx.author and ctx.author.roles:
            if "1176291872143052831" in (str(role) for role in ctx.author.roles):
                help_embed.add_field(name="`Administrative Commands`:",
                                     value="" +
                                           "- `/delete-group` - Completely erase a group from the database, including all members and drops" +
                                           "- `/delete-user` - Delete a user from the database, including all drops and correlations.\n" +
                                           "- `/delete-drop` - Remove a drop from the database by providing its ID.\n" +
                                           "- `/user-info` - View information about a user such as their RSNs, discord affiliation, etc.\n" +
                                           "- `/restart` - Force a complete server restart.", inline=False)
                
        help_embed.add_field(name="Helpful Links",
                             value="[Docs](https://www.droptracker.io/docs) | "+
                             "[Join our Discord](https://www.droptracker.io/discord) | " +
                             "[GitHub](https://www.github.io/joelhalen/droptracker-py) | " + 
                             "[Patreon](https://www.patreon.com/droptracker)", inline=False)
        int_latency_ms = int(ctx.bot.latency * 1000)
        ext_latency_ms = await get_external_latency()
        help_embed.add_field(name="Latency",
                             value=f"Discord API: `{int_latency_ms} ms`\n" +
                                   f"External: `{ext_latency_ms} ms`", inline=False)

        return await ctx.send(embed=help_embed, ephemeral=True)

    @slash_command(name="accounts",
                   description="View your currently claimed RuneScape character names, if you have any")
    async def user_accounts_cmd(self, ctx):
        print("User accounts command...")
        user = session.query(User).filter_by(discord_id=str(ctx.user.id)).first()
        if not user:
            await try_create_user(ctx)
        accounts = session.query(Player).filter_by(user_id=user.user_id)
        account_names = ""
        count = 0
        if accounts:
            for account in accounts:
                count += 1
                last_updated_unix = format_time_since_update(account.date_updated)
                account_names += f"<:totallevel:1179971315583684658> {account.total_level}`" + account.player_name.strip() + f"` (id: {account.player_id})\n> Last updated: <t:{last_updated_unix}:R>\n"
        account_emb = Embed(title="Your Registered Accounts:",
                            description=f"{account_names}(total: `{count}`)")
        # TODO - replace /claim-rsn with an actual clickable command
        account_emb.add_field(name="/claim-rsn",value="To claim another, you can use the `/claim-rsn` command.", inline=False)
        account_emb.set_footer(text="https://www.droptracker.io/")
        await ctx.send(embed=account_emb, ephemeral=True)
    
    @slash_command(name="claim-rsn",
                    description="Claim ownership of your RuneScape account names in the DropTracker database")
    @slash_option(name="rsn",
                  opt_type=OptionType.STRING,
                  description="Please type the in-game-name of the account you want to claim, **exactly as it appears**!",
                  required=True)
    async def claim_rsn_command(self, ctx, rsn: str):
        user = session.query(User).filter_by(discord_id=str(ctx.user.id)).first()
        group = None
        if not user:
            await try_create_user(ctx)
        if ctx.guild:
            guild_id = ctx.guild.id
            group = session.query(Group).filter(Group.guild_id.ilike(guild_id)).first()
        player = session.query(Player).filter(Player.player_name.ilike(rsn)).first()
        if not player:
            try:
                wom_data = await check_user_by_username(rsn)
            except Exception as e:
                print("Couldn't get player data. e:", e)
                return await ctx.send(f"An error occurred claiming your account.\n" +
                                      "Try again later, or reach out in our Discord server",
                                      ephemeral=True)
            if wom_data:
                player, player_name, player_id = wom_data
                try:
                    if group:
                        new_player = Player(wom_id=player_id, 
                                            player_name=rsn, 
                                            user_id=str(user.user_id), 
                                            user=user, 
                                            group=group)
                    else:
                        new_player = Player(wom_id=player_id, 
                                            player_name=rsn, 
                                            user_id=str(user.user_id), 
                                            user=user)
                    session.add(new_player)
                    session.commit()
                except Exception as e:
                    print(f"Could not create a new player:", e)
                    session.rollback()
                finally:
                    return await ctx.send(f"Your account ({player_name}), with ID `{player_id}` has " +
                                         "been added to the database & associated with your Discord account.")
            else:
                return await ctx.send(f"Your account was not found in the WiseOldMan database.\n" +
                                     f"You could try to manually update your account on their website by [clicking here](https://www.wiseoldman.net/players/{rsn}), then try again, or wait a bit.")
        else:
            joined_time = format_time_since_update(player.date_added)
            if str(player.user.user_id) != str(ctx.user.id):
                await ctx.send(f"Uh-oh!\n" +
                               f"It looks like somebody else may have claimed your account {joined_time}!\n" +
                               f"<@{player.user.discord_id}> (discord id: {player.user.discord_id}) currently owns it in our database.\n" + 
                               "If this is some type of mistake, please reach out in our discord server:\n" + 
                               "https://www.droptracker.io/discord",
                               ephemeral=True)
            else:
                await ctx.send(f"You already claimed ", player_name, f"(WOM id: `{player.wom_id}`) {joined_time}\n" + 
                               "\nSomething not seem right?\n" +
                               "Please reach out in our discord server:\n" + 
                               "https://www.droptracker.io/discord",
                               ephemeral=True)
                      
    @slash_command(name="me",
                   description="View your DropTracker account / stats, or create an account if you don't already have one.")
    async def me_command(self, ctx):
        user = session.query(User).filter(User.discord_id.ilike(str(ctx.user.id))).first()
        if user:
            joined_time = format_time_since_update(user.date_updated)
            time_added = ""
            ## only display the last update time if it varies from the time added.
            if user.date_added != user.date_updated:
                time_added = " (" + user.date_added.strftime("%B %d, %Y") + ")"
            me_embed = Embed(title=f"DropTracker statistics for <@{ctx.user.id}>:", 
                             description=f"Tracking since: {joined_time}{time_added}\n" + 
                             f"- Total accounts: `{len(user.players)}`", 
                             color=0x0ff000)
            if user.groups:
                # If user has more than one group
                if len(user.groups) > 1:
                    group_list = ""
                    for group in user.groups:
                        group_list += f"- {group.group_name} (`{len(group.users)}` members)\n"
                    me_embed.add_field(name="Your groups:", value=group_list, inline=False)
                else:
                    # Only one group, so show it separately
                    group = user.groups[0]
                    me_embed.add_field(name="Your group:", value=f"{group.group_name} - (`{len(group.users)}` members)", inline=False)
            else:
                me_embed.add_field(name="You are not part of any groups.",
                                   value="*you can find groups on [our website](https://www.droptracker.io/)",
                                   inline=False)
        else:
            await try_create_user(ctx)
            return
        me_embed.set_author(name="Your Account",
                              url=f"https://www.droptracker.io/profile?discordId={str(ctx.user.id)}",
                              icon_url="https://www.droptracker.io/img/droptracker-small.gif")
        me_embed.set_thumbnail(url="https://www.droptracker.io/img/droptracker-small.gif")
        await ctx.send(embed=me_embed, ephemeral=True)
        #me_embed.set_footer(text="View our documentation to learn more about how to interact with the Discord bot.")
        



# Commands that help configure or change clan-specifics.
class ClanCommands(Extension):
    @slash_command(name="create-group",
                    description="Create a new group with the DropTracker")
    @slash_option(name="group_name",
                  opt_type=OptionType.STRING,
                  description="How would you like your group's name to appear?",
                  required=True)
    @slash_option(name="wom_id",
                  opt_type=OptionType.INTEGER,
                  description="Enter your group's WiseOldMan group ID",
                  required=True)
    # @slash_option(name="group_name",
    #               opt_type=OptionType.STRING,
    #               description="How would you like your group's name to appear?",
    #               required=True)
    @check(is_owner()) # TODO - remove owner-of-bot-only check
    async def create_group_cmd(self, 
                               ctx: SlashContext, 
                               group_name: str,
                               wom_id: int):
        if not ctx.guild:
            return await ctx.send(f"You must use this command in a Discord server")
        if ctx.author_permissions.ALL:
            print("Comparing:")
            user = session.query(User).filter(User.discord_id == ctx.author.id).first()
            if not user:
                return await ctx.send(f"You need to register an account in our database before creating a Group.\n" + 
                                      f"Use </me:{await get_command_id(self.bot, 'me')}> first.")
            guild = session.query(Guild).filter(Guild.guild_id == ctx.guild_id).first()
            if not guild:
                guild = Guild(guild_id=str(ctx.guild_id),
                                  date_added=datetime.now())
                session.add(guild)
                session.commit()
            if guild.group_id != None:
                    return await ctx.send(f"This Discord server is already associated with a DropTracker group.\n" + 
                                        "If this is a mistake, please reach out in Discord", ephemeral=True)
            else:
                group = session.query(Group).filter(Group.wom_id == wom_id).first()
                if group:
                    return await ctx.send(f"This WOM group (`{wom_id}`) already exists in our database.\n" + 
                                        "Please reach out in our Discord server if this appears to be a mistake.",
                                        ephemeral=True)
                else:
                    group = Group(group_name=group_name,
                                wom_id=wom_id,
                                guild_id=guild.guild_id)
                    session.add(group)
                    print("Created a group")
                    user.groups.append(group)
                    session.commit()
            embed = Embed(title="New group created",
                        description=f"Your Group has been created (ID: `{group.group_id}`)")
            embed.add_field(name=f"WOM group `{group.wom_id}` is now assigned to your Discord server `{group.guild_id}`",
                            value=f"<a:loading:1180923500836421715> Please wait while we initialize some things for you...",
                            inline=False)
            embed.set_footer(f"https://www.droptracker.io/discord")
            await ctx.send(f"Success!\n",embed=embed,
                                            ephemeral=True)
            default_config = session.query(GroupConfiguration).filter(GroupConfiguration.group_id == 1).all()
            ## grab the default configuration options from the database
            new_config = []
            for option in default_config:
                option_value = option.config_value
                if option.config_key == "clan_name":
                    option_value = ctx.guild.name
                default_option = GroupConfiguration(
                    group_id=group.group_id,
                    config_key=option.config_key,
                    config_value=option_value,
                    updated_at=datetime.now(),
                    group=group
                )
                new_config.append(default_option)
            try:
                session.add_all(new_config)
                session.commit()
            except Exception as e:
                session.rollback()
                print("Error occured trying to save configs::", e)
                return await ctx.send(f"Unable to create the default configuration options for your clan.\n" + 
                                      f"Please reach out in the DropTracker Discord server.",
                                      ephemeral=True)
            
            await asyncio.sleep(5)
            await ctx.send(f"To continue setting up, please use </group-config:{await get_command_id(self.bot, 'group-config')}>",
                            ephemeral=True)
        else:
            await ctx.send(f"You do not have the necessary permissions to use this command inside of this Discord server.\n" + 
                           "Please ask the server owner to execute this command.",
                           ephemeral=True)

    @slash_command(name="group-config",
                   description="Begin configuring your DropTracker group.")
    async def start_config_cmd(self, ctx: SlashContext):
        guild = session.query(Guild).filter(Guild.guild_id == ctx.guild_id).first()
        if not guild:
            return await ctx.send(f"You have not yet registered this clan. Use </group-config:{await get_command_id(self.bot, 'create-group')}>")
        else:
            group = session.query(Group).filter(Group.group_id == guild.group_id).first()
            if not group:
                return await ctx.send(f"An unexpected error occurred.")
            else:
                buttons = []
                embed=Embed(title="<:settings:1213800934488932373> DropTracker Group Configuration <:settings:1213800934488932373>",
                            description=f"To cancel your current **group configuration** session at any time, type `STOP`.")
                embed.add_field(name="How to use:",
                                value="Each config option has its respective 'key'.\n" + 
                                "To change a setting, simply type: edit `key` new_value.\n" + 
                                "To move between pages, use the buttons below.",
                                inline=False)
                embed.add_field(name="Directory",
                                value="Page 1: General Settings\n" + 
                                "Page 2: Notifications\n" + 
                                "Page 3: Channels & etc.",
                                inline=False)
                embed.add_field(name="Settings:",
                                value="**Authed Roles** (key: `authed`)\n" + 
                                        "A list of authorized Discord Server roles you want to have *administrative* access to the DropTracker in your group.\n" + 
                                "Lootboard_message_id\n" + 
                                "\n" + 
                                "\n" + 
                                "\n",
                                inline=True)
                next_page = Button(style=ButtonStyle.PRIMARY,
                                    label="Next Page",
                                    custom_id="group_cfg_pg_2")
                exit_button = Button(style=ButtonStyle.DANGER,
                                        label="Exit Configuration",
                                        custom_id="exit_cfg_init")
                buttons = [next_page, exit_button]
                message = await ctx.send(f"You **must** type `STOP` to finish editing your group configuration.\n**I will continue listening for messages from you until then!**", 
                                embeds=embed, 
                                components=[buttons],
                                ephemeral=True)
                redis_client.set(f"config:{str(ctx.user.id)}:group",f"active:{str(group.group_id)}:{str(message.id)}")
            


# Commands to help moderate the DropTracker as a whole, 
# meant to be used by admins in the droptracker.io discord
class AdminCommands(Extension):
    @slash_command(name="global-board",
                   description="Generate a global server board")
    @slash_option(name="partition",
                  description="Which partition do you want to generate a board for",
                  opt_type=interactions.OptionType.STRING)
    @check(interactions.is_owner())
    async def visualize_db(self, ctx: SlashContext, partition: str = datetime.now().year * 100 + (datetime.now().month)):
        await generate_server_board(self.bot, group_id=1, partition=partition)
        pass

    @slash_command()
    @check(interactions.is_owner())
    async def stress_test(self, ctx: SlashContext):
        response = await ctx.send(f"Trying to find all drops in the database and perform sorting")
        time_start = time.time()
        try:
            all_drops = await db.lootboard_drops()
        except Exception as e:
            print("Exception:", e)
        finally:
            time_taken = time.time() - time_start
        print("Done finding drops.")
        return await response.reply(f"Found all drops. Length: {len(all_drops)}, \nTime taken: <t:{int(time_taken)}:R>\n")


async def try_create_user(ctx: SlashContext):
    discord_id = ctx.user.id
    username = ctx.user.username
    try:
        user = db.create_user(str(discord_id), str(username))
    except Exception as e:
        return await ctx.send(f"An error occurred attempting to register your account in the database.\n" + 
                                f"Please reach out for help: https://www.droptracker.io/discord",ephemeral=True)
    return await ctx.send(f"Your account has been registered. (DT ID: `{user.user_id}`)")


async def get_external_latency():
        host = "amazon.com"
        ping_command = ["ping", "-c", "1", host]

        try:
            output = subprocess.check_output(ping_command, stderr=subprocess.STDOUT, universal_newlines=True)
            if "time=" in output:
                ext_latency_ms = output.split("time=")[-1].split(" ")[0]
                return ext_latency_ms
        except subprocess.CalledProcessError:
            return "N/A"  

        return "N/A"