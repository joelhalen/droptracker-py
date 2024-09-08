import interactions
import aiohttp
import aiofiles
from interactions import Embed, Client, listen, ChannelType, Button, ButtonStyle
from interactions.api.events import MessageCreate, Component
from db.models import User, Group, Guild, Player, Drop, session, ItemList, Webhook, NpcList
from utils.wiseoldman import check_user_by_id, check_user_by_username, check_group_by_id
import re
import os

from utils.format import format_time_since_update, format_number, get_command_id, get_extension_from_content_type

from datetime import datetime, timedelta

from utils.redis import RedisClient
from db.ops import DatabaseOperations

db = DatabaseOperations()
redis_client = RedisClient()

ignored_list = [] # temporary implementation of a source blacklist

async def send_update_message(bot: interactions.Client, total_added, current_id):
    channel = await bot.fetch_channel(channel_id=1281734796116099155)
    update_embed = interactions.Embed(title="New drops added",
                                      description="A cycle of the redis cache update has completed.")
    update_embed.set_thumbnail(url="https://www.droptracker.io/img/droptracker-small.gif")
    update_embed.add_field(name=f"Added a total of {total_added} new entries.",
                           value=f"Currently up to id #{current_id}")
    await channel.send(embed=update_embed)

webhook_channels = []
last_webhook_refresh = datetime.now() - timedelta(hours=24)
npc_list = {} # - stores a dict of the npc's and their corresponding IDs to prevent excessive querying
player_list = {} # - stores a dict of player name:ids, and their last refresh from the DB.


async def message_processor(bot: interactions.Client, event: interactions.events.MessageCreate):
    global webhook_channels
    global last_webhook_refresh
    global npc_list
    global player_list
    global ignored_list
    global drop_ct
    message = event.message
    if message.author.system:  # or message.author.bot:
        return
    if message.author.id == bot.user.id:
        return
    if message.channel.type == ChannelType.DM or message.channel.type == ChannelType.GROUP_DM:
        return
    
    channel_id = message.channel.id
    # if str(message.channel.id) == "1262137292315688991":
    if datetime.now() - last_webhook_refresh > timedelta(hours=1):
        # Assuming webhook_channels is a list of extracted webhook IDs
        webhook_channels.clear()

        # Query your database to get the webhook URLs
        webhooks = session.query(Webhook.webhook_url).all()

        # Regex pattern to capture the webhook ID from the URL
        webhook_id_pattern = r'/webhooks/(\d+)/'

        # Loop through each webhook URL from the database
        for webhook in webhooks:
            url = webhook[0]  # Assuming webhook[0] holds the URL from the query
            match = re.search(webhook_id_pattern, url)  # Search for the ID pattern in the URL
            if match:
                webhook_id = match.group(1)  # Extract the matched webhook ID
                webhook_channels.append(int(webhook_id))  # Add the webhook ID to the list

        # Update last webhook refresh time after processing
        last_webhook_refresh = datetime.now()
    if int(message.webhook_id) in webhook_channels:
    # if int(channel_id) in webhook_channels:
        item_name = ""
        player_name = ""
        item_id = 0
        npc_name = "none"
        value = 0
        quantity = 0
        sheet_id = ""
        source_type = ""
        imageUrl = ""
        for embed in message.embeds:
            field_names = [field.name for field in embed.fields]

            if "type" in field_names:
                field_values = [field.value.lower().strip() for field in embed.fields]
                rsn = ""

                if "collection_log" in field_values:
                    for field in embed.fields:
                        if field.name == "item":
                            item_name = field.value
                        elif field.name == "player":
                            rsn = field.value
                        elif field.name == "item_id":
                            itemId = field.value
                        elif field.name == "source":
                            npcName = field.value
                        elif field.name == "rarity":
                            if field.value != "OptionalDouble.empty":
                                rarity = field.value
                            else:
                                rarity = ""
                        elif field.name == "sheet":
                            sheet_id = field.value
                        elif field.name == "kc":
                            if field.value != "null":
                                kc = field.value
                            else:
                                kc = 0

                    imageUrl = ""
                    if rsn == "":
                        print("Did not find an RSN")
                        return
                    if message.attachments:
                        for attachment in message.attachments:
                            if attachment.url:
                                file_extension = get_extension_from_content_type(attachment.content_type)
                                file_name = f"{item_name}.{file_extension}"
                                fn1, fn2 = await download_player_image("clog", file_name, rsn, attachment.url,
                                                                       file_extension)

                                imageUrl = f"M:\\droptracker-react\\droptracker-react\\public\\img\\{rsn}\\clog\\{item_name}.{file_extension}"
                                break
                    print("Final item name:", item_name)
                    clog_data = {
                        "itemName": item_name,
                        "rsn": rsn,
                        "itemId": itemId,
                        "rarity": rarity,
                        "kc": kc,
                        "npcName": npcName,
                        "imageUrl": imageUrl
                    }
                    print("Created data", clog_data)
                    await websocket_client.send_add_log_slot(clog_data)
                    continue
                elif "combat_achievement" in field_values:
                    pass
                elif "personal_best" in field_values:
                    pass
                elif embed.title and "received some drops" in embed.title or "drop" in field_values:
                    # print("Legacy drop")
                    if embed.fields:
                        for field in embed.fields:
                            if field.name == "player":
                                player_name = field.value.strip()
                            elif field.name == "item":
                                item_name = field.value.strip()
                            elif field.name == "id":
                                item_id = int(field.value.strip())
                            elif field.name == "source":
                                npc_name = field.value.strip()
                                if npc_name in ignored_list:
                                    return
                            elif field.name == "value":
                                if field.value:
                                    value = int(field.value)
                                else:
                                    value = 0
                            elif field.name == "quantity":
                                if field.value:
                                    quantity = int(field.value)
                                else:
                                    quantity = 1
                            elif field.name == "sheet_id" or field.name == "sheet":
                                sheet_id = field.value
                            elif field.name == "webhook" and len(field.value) > 10:
                                pass
                        if message.attachments:
                            for attachment in message.attachments:
                                if attachment.url:
                                    file_extension = get_extension_from_content_type(attachment.content_type)
                                    file_name = f"{item_name}"
                                    fn1, fn2 = await download_player_image("drops", file_name, player_name,
                                                                           attachment.url,
                                                                           file_extension)
                                    imageUrl = f"https://www.droptracker.io/img/user-upload/{player_name}/drops/{fn2}"
                                    break
                        if npc_name in npc_list:
                            npc_id = npc_list[npc_name]
                        else:
                            npc = session.query(NpcList.npc_id).filter(NpcList.npc_name == npc_name).first()
                            if not npc:
                                print(f"NPC {npc_name} not found in the database. Calling confirm_new_npc.")
                                await confirm_new_npc(bot, npc_name, player_name, item_name, value)
                                return  # Return here since the NPC creation might be deferred
                            else:
                                npc_list[npc_name] = npc.npc_id
                                npc_id = npc.npc_id

                        # Now process the player
                        if player_name not in player_list:
                            player = session.query(Player.player_id).filter(Player.player_name == player_name).first()
                            if not player:
                                wom_player, player_name, wom_player_id = await check_user_by_username(player_name)
                                if not wom_player.latest_snapshot:
                                    print(f"Failed to find or create player via WOM: {player_name}. Aborting.")
                                    return  # Abort if the player was not found or created
                                player: Player = session.query(Player).filter(Player.wom_id == wom_player_id).first()
                                if player:
                                    old_name = player.player_name
                                    player.player_name = player_name
                                    session.commit()
                                    await name_change_message(bot, player_name, player.player_id, old_name)
                                else:
                                    overall = wom_player.latest_snapshot.data.skills.get('overall')
                                    total_level = overall.level
                                    new_player = Player(wom_id=wom_player_id, player_name=player_name, total_level=total_level)
                                    session.add(new_player)
                                    await new_player_message(bot, player_name)
                                    session.commit()
                                    player_list[player_name] = new_player.player_id
                                    print(f"Created new player {player_name} with id {new_player.player_id}.")
                            else:
                                player_list[player_name] = player.player_id
                                
                        player_id = player_list[player_name]
                        item = redis_client.get(item_id)
                        if not item:
                            item = session.query(ItemList.item_id).filter(ItemList.item_id == item_id).first()
                        if item:
                            redis_client.set(item_id, item[0])
                        else:
                            await confirm_new_item(bot, item_name, player_name, item_id, npc_name, value)
                            return
                        # Now create the drop object
                        await db.create_drop_object(
                            item_id=item_id,
                            player_id=player_id,
                            date_received=datetime.now(),
                            npc_id=npc_id,
                            value=value,
                            quantity=quantity
                        )
                        return
    else:
        cache_key = f"config:{str(message.author.id)}:group"

        # Retrieve the value stored in Redis for this key
        value = redis_client.get(cache_key)

        if value:
            # Decode the value from bytes to string if necessary
            value = value.decode('utf-8')
            
            # Split the value based on the ':' delimiter
            parts = value.split(':')
            
            if len(parts) == 3 and parts[0] == 'active':
                group_id = parts[1]
                message_id = parts[2]
                print(f"Group ID: {group_id}, Message ID: {message_id}")
                await handle_config(bot, event, group_id, message_id)
            else:
                print("Invalid value format.")
        # else:
        #     print("No value found for this key.")
    

async def download_player_image(submission_type: str, 
                                file_name: str,
                                player_name: str,
                                attachment_url: str,
                                file_extension: str):
    base_dir = "/store/droptracker/disc/static/assets/img/user-upload/"

    def generate_unique_filename(directory, file_name, ext):
        base_name = file_name
        counter = 1
        unique_file_name = f"{base_name}.{ext}"
        while os.path.exists(os.path.join(directory, unique_file_name)):
            unique_file_name = f"{base_name}_{counter}.{ext}"
            counter += 1
        return unique_file_name

    # Ensure the directory structure exists
    directory_path = os.path.join(base_dir, player_name, submission_type)
    os.makedirs(directory_path, exist_ok=True)

    # Generate unique filename for the download
    unique_file_name = generate_unique_filename(directory_path, file_name, file_extension)
    download_path = os.path.join(directory_path, unique_file_name)

    # Download the file asynchronously
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment_url) as response:
                if response.status == 200:
                    async with aiofiles.open(download_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            await f.write(chunk)
        print(f"File saved at: {download_path}")
        return unique_file_name
    except Exception as e:
        print(f"Failed to download file: {e}")
        return None
    

async def new_player_message(bot: interactions.Client, player_name):
    channel_id = 1281734796116099155
    channel = await bot.fetch_channel(channel_id=1281734796116099155)
    await channel.send(embeds=Embed(title="New player added",
                                    description=f"{player_name} has made their first appearance in the database.",
                                    color=0x00ff00))
    
async def name_change_message(bot, new_name, player_id, old_name):
    channel_id = 1281734796116099155
    channel = await bot.fetch_channel(channel_id=1281734796116099155)
    await channel.send(embeds=Embed(title="Name changed",
                                    description=f"[{player_id}] `{old_name}` -> `{new_name}`",
                                    color=0x00ff00))
                                
    
async def confirm_new_npc(bot: interactions.Client, npc_name, player_name, item_name, value):
    channel_id = 1281734796116099155
    channel = await bot.fetch_channel(channel_id=1281734796116099155)
    confirmation_embed = Embed(title="New NPC detected",
                            description=f"`{player_name}` received a drop from a new npc:",
                            color=0x00ff00)
    confirmation_embed.add_field(name="Details:",
                                 value=f"Name: {npc_name}\n" + 
                                 f"Item/value: {item_name} (`{value}` gp)", inline=False)
    confirm_button = interactions.Button(style=interactions.ButtonStyle.PRIMARY,
                                         label="Add this NPC",
                                         custom_id=f"confirm_npc_{npc_name}")
    deny_button = interactions.Button(style=interactions.ButtonStyle.DANGER,
                                         label="Ignore this NPC",
                                         custom_id=f"deny_npc_{npc_name}")
    await channel.send(embed=confirmation_embed,
                       components=[deny_button, confirm_button])

async def confirm_new_item(bot: interactions.Client, item_name, player_name, item_id, npc_name, value):
    channel_id = 1281734796116099155
    channel = await bot.fetch_channel(channel_id=1281734796116099155)
    confirmation_embed = Embed(title="New item detected",
                            description=f"`{player_name}` received a new drop:",
                            color=0x00ff00)
    confirmation_embed.add_field(name=f"Received from `{npc_name}`",
                                 value=f"Item name: `{item_name}`\n" + 
                                 f"Item id/value: `{item_id}` (`{value}` gp)", inline=False)
    confirmation_embed.set_thumbnail(f"https://static.runelite.net/cache/item/icon/{item_id}.png")
    confirm_button = interactions.Button(style=interactions.ButtonStyle.PRIMARY,
                                         label="Add this item",
                                         custom_id=f"confirm_item_{item_name}__{item_id}")
    deny_button = interactions.Button(style=interactions.ButtonStyle.DANGER,
                                         label="Ignore this item",
                                         custom_id=f"add_item_{item_name}__{item_id}")
    await channel.send(embed=confirmation_embed,
                       components=[deny_button, confirm_button])


async def handle_config(bot: interactions.Client,
                        event: interactions.events.MessageCreate,
                    group_id, message_id):
    message: interactions.Message = bot.get_message(channel_id=int(event.channel.id),
                              message_id=message_id)
    if not message:
        print("Couldn't find the previous config ...")
    else:
        if "STOP" in event.message.content:
            cache_key = f"config:{str(message.author.id)}:group"
            redis_client.set(cache_key, "cancelled")
            try:
                await message.delete()
            except Exception:
                pass
            return await event.message.reply(f"You have stopped configuring your Group.")
        embed=Embed(title="<:settings:1213800934488932373> DropTracker Group Configuration <:settings:1213800934488932373>",
                        description=f"To cancel your current **group configuration** session at any time, type `STOP`.")
        embed.add_field(name="How to use:",
                            value="Each config option has its respective 'key'.\n" + 
                            "To change a setting, simply type: edit `key` new_value.\n" + 
                            "To move between pages, use the buttons below.",
                            inline=False)
        current_state = 0 if ["init" in component.custom_id for component in message.components] else 1
        if current_state == 0:
            buttons = []
            embed.add_field(name="Page #1 (General)\nSettings:",
                            value="**Authed Roles** (key: `authed`)\n" + 
                                    "A list of authorized Discord Server roles you want to have *administrative* access to the DropTracker in your group.\n" + 
                                    "```Example: 'authed <id>' or 'authed @pinged-role-here'```"
                            "\n" + 
                            "\n" + 
                            "\n" + 
                            "\n",
                            inline=True)
            next_page = Button(style=ButtonStyle.PRIMARY,
                                label="Page #2",
                                custom_id="group_cfg_pg_2")
            exit_button = Button(style=ButtonStyle.DANGER,
                                    label="Exit Configuration",
                                    custom_id="exit_cfg_init")
            buttons = [next_page, exit_button]
            message = await message.edit(f"You **must** type `STOP` to finish editing your group configuration.\n**I will continue listening for messages from you until then!**", 
                            embeds=embed, 
                            components=[buttons],
                            ephemeral=True)
        else:
            pass


