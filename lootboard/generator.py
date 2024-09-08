import asyncio
import csv
import calendar
import json
import os
import traceback
from datetime import datetime
from db.models import Player, ItemList, session
from io import BytesIO

import aiohttp
import interactions
from PIL import Image, ImageFont, ImageDraw

from utils.redis import RedisClient
from utils.wiseoldman import fetch_group_members
from db.ops import DatabaseOperations

from utils.format import format_number

redis_client = RedisClient()
db = DatabaseOperations()
yellow = (255, 255, 0)
black = (0, 0, 0)
font_size = 30

rs_font_path = "static/assets/fonts/runescape_uf.ttf"
tracker_fontpath = 'static/assets/fonts/droptrackerfont.ttf'
main_font = ImageFont.truetype(rs_font_path, font_size)

async def get_drops_for_group(player_ids, partition: str = datetime.now().year * 100 + (datetime.now().month)):
    """ Returns the drops stored in redis cache 
        for the specific list of player_ids
    """
    group_items = {}
    recent_drops = []
    total_loot = 0
    player_totals = {}
    print("Getting drops for partition", partition)

    for player_id in player_ids:
        total_items_key_all = f"player:{player_id}:{partition}:total_items"
        npc_totals_key_all = f"player:{player_id}:{partition}:npc_totals"
        total_loot_key_all = f"player:{player_id}:{partition}:total_loot"
        recent_items_key_all = f"player:{player_id}:{partition}:recent_items"

        # Get total items and merge dictionaries
        total_items = {k.decode('utf-8'): v.decode('utf-8') for k, v in redis_client.client.hgetall(total_items_key_all).items()}
        for key, value in total_items.items():
            # value will be in the format "quantity,value"
            quantity, total_value = map(int, value.split(','))
            if player_id not in player_totals:
                player_totals[player_id] = int(total_value)
            else:
                player_totals[player_id] += int(total_value)

            
            # Update group_items to store both quantity and total_value
            if key in group_items:
                # If the item already exists in group_items, sum both quantity and value
                existing_quantity, existing_value = map(int, group_items[key].split(','))
                new_quantity = existing_quantity + quantity
                new_total_value = existing_value + total_value
                group_items[key] = f"{new_quantity},{new_total_value}"
            else:
                # If the item is new, add it directly
                group_items[key] = f"{quantity},{total_value}"

            # Aggregate total value across all items for the group
            total_loot += total_value

        # Get NPC totals (assuming you may want to aggregate this too)
        npc_totals = {k.decode('utf-8'): v.decode('utf-8') for k, v in redis_client.client.hgetall(npc_totals_key_all).items()}

        # Add to the total loot from Redis
        loot = redis_client.get(total_loot_key_all)
        if loot:
            total_loot += int(loot)

        # Get recent items and decode JSON
        recent_items = [json.loads(item.decode('utf-8')) for item in redis_client.client.lrange(recent_items_key_all, 0, -1)]
        recent_drops.extend(recent_items)

    return group_items, player_totals, recent_drops, total_loot


async def generate_server_board(bot, group_id: int, partition: str = datetime.now().year * 100 + (datetime.now().month)):
    # Fetch clan settings first (commented out for now)
    # clan_settings = await get_clan_settings(server_id)
    # if not clan_settings:
    #     return

    loot_board_style = 1  # TODO: Implement other boards eventually

    # Load background image based on the board style
    bg_img, draw = load_background_image("/store/droptracker/disc/lootboard/bank-new-clean-dark.png")

    # Fetch player WOM IDs and associated Player IDs
    player_wom_ids = await fetch_group_members(group_id)
    player_ids = await associate_player_ids(player_wom_ids)

    # Get the drops, recent drops, and total loot for the group
    
    group_items, player_totals, recent_drops, total_loot = await get_drops_for_group(player_ids, partition)

    # Draw elements on the background image
    bg_img = await draw_drops_on_image(bg_img, draw, group_items, group_id)  # Pass `group_items` here
    bg_img = await draw_headers(bot, group_id, total_loot, bg_img, draw)  # Draw headers
    bg_img = await draw_recent_drops(bg_img, draw, recent_drops, min_value=2500000)  # Draw recent drops, with a minimum value
    bg_img = await draw_leaderboard(bg_img, draw, player_totals)  # Draw leaderboard
    save_image(bg_img, group_id)  # Save the generated image

    return bg_img


def get_year_month_string():
    return datetime.now().strftime('%Y-%m')


async def draw_headers(bot: interactions.Client, group_id, total_loot, bg_img, draw):
    current_month = datetime.now().month
    month_string = calendar.month_name[current_month].lower()
    current_year_month = datetime.now().strftime('%Y-%m')
    this_month = format_number(total_loot)
    # recents = f"Recent Submissions"
    if int(group_id) == 1:
        title = f"Tracked Drops - All Players ({month_string.capitalize()}) - {this_month}"
    else:
        #server = bot.get_guild(server_id)
        server_name = "Nameless"
        title = f"{server_name}'s Tracked Drops for {month_string.capitalize()} ({this_month})"

    # Calculate text size using textbbox
    bbox = draw.textbbox((0, 0), title, font=main_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    center_header_x = text_width / 2
    center_header_y = text_height / 2
    bg_img_w, bg_img_h = bg_img.size
    center_bg = bg_img_w / 2
    head_loc_x = int(center_bg - center_header_x)
    head_loc_y = 20
    draw.text((head_loc_x, head_loc_y), title, font=main_font, fill=yellow, stroke_width=2, stroke_fill=black)
    return bg_img


def load_background_image(filepath):
    bg_img = Image.open(filepath)
    draw = ImageDraw.Draw(bg_img)
    return bg_img, draw


async def draw_leaderboard(bg_img, draw, player_totals):
    """
    Draws the leaderboard for players with their total loot values.
    
    :param bg_img: The background image to draw the leaderboard on.
    :param draw: The ImageDraw object used to draw the text.
    :param player_totals: Dictionary of player names and their total loot value.
    :return: Updated background image with the leaderboard drawn on it.
    """
    # Sort players by total loot value in descending order, taking the top 12
    top_players = sorted(player_totals.items(), key=lambda x: x[1], reverse=True)[:12]
    
    # Define text positioning
    name_x = 141
    name_y = 228
    pet_font = ImageFont.truetype(rs_font_path, 15)
    first_name = True

    for i, (player, total) in enumerate(top_players):
        # Format player loot totals
        # total_value = int(total)
        total_loot_display = format_number(total)

        # Create rank, name, and loot text
        rank_num_text = f'{i + 1}'
        player_obj = session.query(Player.player_name).filter(Player.player_id == player).first()
        if not player_obj:
            print("Player with ID", player, " not found.")
            player_rsn = f"Name not found...."
        else:
            player_rsn = player_obj.player_name
        rsn_text = f'{player_rsn}'
        gp_text = f'{total_loot_display}'

        # Determine positions for rank, name, and total loot text
        rank_x, rank_y = (name_x - 104), name_y
        quant_x, quant_y = (name_x + 106), name_y

        # Calculate center for loot (gp_text) and rank_num_text
        quant_bbox = draw.textbbox((0, 0), gp_text, font=pet_font)
        center_q_x = quant_x - (quant_bbox[2] - quant_bbox[0]) / 2

        rsn_bbox = draw.textbbox((0, 0), rsn_text, font=pet_font)
        center_x = name_x - (rsn_bbox[2] - rsn_bbox[0]) / 2

        rank_bbox = draw.textbbox((0, 0), rank_num_text, font=pet_font)
        rank_mid_x = rank_x - (rank_bbox[2] - rank_bbox[0]) / 2

        # Draw text for rank, name, and total loot
        draw.text((center_x, name_y), rsn_text, font=pet_font, fill=yellow)
        draw.text((rank_mid_x, rank_y), rank_num_text, font=pet_font, fill=yellow)
        draw.text((center_q_x, quant_y), gp_text, font=pet_font, fill=yellow)

        # Update Y position for the next player
        if not first_name:
            name_y += 22
        else:
            name_y += 22
            first_name = False

    return bg_img

async def draw_drops_on_image(bg_img, draw, group_items, group_id):
    """
    Draws the items on the image based on the quantities provided in group_items.
    
    :param bg_img: The background image to draw on.
    :param draw: The ImageDraw object to draw with.
    :param group_items: Dictionary of item_id and corresponding quantities/values.
    :param group_id: The group ID to determine specific placement rules if needed.
    :return: Updated background image with item images and quantities.
    """
    locations = {}
    small_font = ImageFont.truetype(rs_font_path, 18)
    amt_font = ImageFont.truetype(rs_font_path, 25)

    # Load item positions from the CSV file
    with open("data/item-mapping.csv", 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            locations[i] = row

    # Sort items by value and limit to top 32
    sorted_items = sorted(group_items.items(), key=lambda x: int(x[1]) if isinstance(x[1], int) else int(x[1].split(',')[1]), reverse=True)[:32]

    for i, (item_id, totals) in enumerate(sorted_items):
        # print("Item:", sorted_items[i])
        # Get quantity and total value from Redis data
        # print(item_id, totals)
        quantity, total_value = map(int, totals.split(','))

        # Get the item's position from the CSV file
        current_pos_x = int(locations[i]['x'])
        current_pos_y = int(locations[i]['y'])
        img_coords = (current_pos_x - 5, current_pos_y - 12)

        # Load the item image based on the item_id
        item_img = await load_image_from_id(int(item_id))
        if not item_img:
            continue  # Skip if no image found

        # Resize and paste the item image onto the backgroundcurrent_width, current_height = item_img.size
        current_width, current_height = item_img.size
        scale_factor = 1.8
        new_width = round(current_width * scale_factor)
        new_height = round(current_height * scale_factor)
        item_img_resized = item_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        fixed_img = center_image(item_img_resized, 75, 75)
        bg_img.paste(fixed_img, img_coords, fixed_img)

        # Format the quantity for display (e.g., 1K, 1M)
        value_str = format_number(total_value)
        quantity_str = format_number(quantity)
        ctr_x = (current_pos_x + 1)
        ctr_y = (current_pos_y - 10)
        num_x, num_y = ctr_x, ctr_y + 45

        # Draw the quantity text
        ctr_x, ctr_y = current_pos_x + 1, current_pos_y - 10
        draw.text((num_x, num_y), value_str, font=small_font, fill=yellow, stroke_width=1, stroke_fill=black)
        # Counter
        draw.text((ctr_x, ctr_y), quantity_str, font=amt_font, fill=yellow, stroke_width=2, stroke_fill=black)
       #draw.text((ctr_x, ctr_y + 45), value_str, font=amt_font, fill=yellow, stroke_width=2, stroke_fill=black)

    return bg_img


async def draw_recent_drops(bg_img, draw, recent_drops, min_value):
    """
    Draw recent drops on the image, filtering based on a minimum value.
    
    :param bg_img: Background image to draw on.
    :param draw: ImageDraw object to draw elements.
    :param recent_drops: List of recent drops to process.
    :param min_value: The minimum value of drops to be displayed.
    """
    # print("Recent drops:", recent_drops)
    
    # Filter the drops based on their value, keeping only those above the specified min_value
    filtered_recents = [drop for drop in recent_drops if drop['value'] >= min_value]
    
    # Sort drops by date in descending order and limit to the most recent 12 drops
    sorted_recents = sorted(filtered_recents, key=lambda x: x['date_added'], reverse=True)[:12]
    
    small_font = ImageFont.truetype(rs_font_path, 18)
    recent_locations = {}
    
    # Load locations for placing recent items on the board
    with open("data/recent-mapping.csv", 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            recent_locations[i] = row
    
    # Loop through the sorted recent drops and display them
    user_names = {}
    for i, data in enumerate(sorted_recents):
        user_id = data["player_id"]

        # Check if user_id is already cached in the user_names dictionary
        if user_id not in user_names:
            # Query the player's name from the database
            user_obj = session.query(Player.player_name).filter(Player.player_id == user_id).first()

            # Handle case where the player is not found in the database
            if user_obj:
                user_names[user_id] = user_obj.player_name
            else:
                user_names[user_id] = "Unknown"  # Fallback in case the user doesn't exist
        username = user_names[user_id]
        value = data["value"]
        date_string = data["date_added"]
        try:
            # Try with microseconds
            date_obj = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            # Fallback to without microseconds
            date_obj = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S')
        
        # Get the item image based on the item name or ID
        item_id = data["item_id"]
        item_img = await load_image_from_id(item_id)
        if not item_img:
            continue
        
        # Get the x, y coordinates for the item based on recent_locations
        current_pos_x = int(recent_locations[i]['x'])
        current_pos_y = int(recent_locations[i]['y'])
        
        # Resize and paste the item image onto the background
        scale_factor = 1.8
        new_width = round(item_img.width * scale_factor)
        new_height = round(item_img.height * scale_factor)
        item_img_resized = item_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        fixed_item_img = center_image(item_img_resized, 75, 75)
        img_coords = (current_pos_x - 5, current_pos_y - 12)
        bg_img.paste(fixed_item_img, img_coords, fixed_item_img)
        
        # Draw text for username and time since the drop
        center_x = (current_pos_x + 1)
        center_y = (current_pos_y - 10)
        current_time = datetime.now()
        time_since = current_time - date_obj
        days, hours, minutes = time_since.days, time_since.seconds // 3600, (time_since.seconds // 60) % 60
        
        if days > 0:
            time_since_disp = f"({days}d {hours}h)"
        elif hours > 0:
            time_since_disp = f"({hours}h {minutes}m)"
        else:
            time_since_disp = f"({minutes}m)"
        
        draw.text((center_x + 5, center_y), username, font=small_font, fill=yellow, stroke_width=1, stroke_fill=black)
        draw.text((current_pos_x, current_pos_y + 35), time_since_disp, font=small_font, fill=yellow)
    return bg_img

def center_image(image, width, height):
    # Create a new image with the desired dimensions and a transparent background
    centered_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    # Calculate the position where the original image should be pasted to be centered
    paste_x = (width - image.width) // 2
    paste_y = (height - image.height) // 2
    # Paste the original image onto the new image at the calculated position
    centered_image.paste(image, (paste_x, paste_y))
    return centered_image


def save_image(image, server_id):
    # Save logic here
    os.makedirs(f"/store/droptracker/disc/static/clans/{server_id}", exist_ok=True)
    image.save(f"/store/droptracker/disc/static/clans/{server_id}/loot_board.png")
    # image.save(f'data/{server_id}/loot-board.png')


async def load_image_from_id(item_id):
    if item_id == "None" or item_id is None or not isinstance(item_id, int):
        return None
    file_path = f"/store/droptracker/disc/static/assets/img/itemdb/{item_id}.png"
    loop = asyncio.get_event_loop()
    try:
        # Run the blocking Image.open operation in a thread pool
        image = await loop.run_in_executor(None, Image.open, file_path)
        return image
    except Exception as e:
        print(f"The following file path: {file_path} produced an error: {e}")
        return None


async def load_rl_cache_img(item_id):
    url = f"https://static.runelite.net/cache/item/icon/{item_id}.png"
    try:
        ## save it here
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                # Ensure the request was successful
                if response.status != 200:
                    print(f"Failed to fetch image for item ID {item_id}. HTTP status: {response.status}")
                    return None

                # Read the response content
                image_data = await response.read()

                # Load the image data into a PIL Image object
                image = Image.open(BytesIO(image_data))
                file_path = f"/store/droptracker/disc/static/assets/img/itemdb/{item_id}.png"
                # print("Saving")
                image.save(file_path, "PNG")
                return image

    except Exception as e:
        print("Unable to load the item.")
    finally:
        await aiohttp.ClientSession().close()

async def associate_player_ids(player_wom_ids):
    # Query the database for all players' WOM IDs and Player IDs
    all_players = session.query(Player.wom_id, Player.player_id).all()
    
    # Create a mapping of WOM ID to Player ID
    db_wom_to_ids = [{"wom": player.wom_id, "id": player.player_id} for player in all_players]
    
    # Filter out the Player IDs where the WOM ID matches any of the given `player_wom_ids`
    matched_ids = [player['id'] for player in db_wom_to_ids if player['wom'] in player_wom_ids]
    
    return matched_ids