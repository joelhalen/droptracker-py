# import asyncio
# import csv
# import calendar
# import json
# import os
# import traceback
# from datetime import datetime
# from io import BytesIO

# import aiohttp
# import interactions
# from PIL import Image, ImageFont, ImageDraw

# from utils import items
# from utils.redis import RedisClient
# from db.ops import DatabaseOperations

# from utils.format import format_number

# redis_client = RedisClient()
# db = DatabaseOperations()
# yellow = (255, 255, 0)
# black = (0, 0, 0)
# font_size = 30

# rs_font_path = "assets/font/runescape_uf.ttf"
# tracker_fontpath = 'assets/font/droptrackerfont.ttf'
# main_font = ImageFont.truetype(rs_font_path, font_size)


# async def generate_server_board(bot, server_id: int):
#     # Fetch clan settings first
#     #clan_settings = await get_clan_settings(server_id)
#     #if not clan_settings:
#         #return

#     #settings = json.loads(clan_settings['clanSettings'])

#     loot_board_style = 1 ## TODO == implement other boards eventually
#     if loot_board_style == 1:
#         bg_img, draw = load_background_image("assets/img/bank-new-clean-dark.png")
#     elif loot_board_style == 2:
#         bg_img, draw = load_background_image("assets/img/bank-new-clean.png")
#     else:
#         bg_img, draw = load_background_image("assets/img/bank-clean.png")
    
#     drops_data = await db.find_all_drops()

#     drops_list, player_totals, recent_drops, total_loot = process_drops_data(drops_data, settings)

#     # Draw elements on the background image
#     bg_img = await draw_drops_on_image(bg_img, draw, drops_list)
#     bg_img = await draw_headers(bot, server_id, settings, total_loot, bg_img, draw)
#     bg_img = await draw_recent_drops(bg_img, draw, recent_drops)
#     bg_img = await draw_leaderboard(bg_img, draw, player_totals)
#     save_image(bg_img, server_id)

#     return bg_img


# def get_year_month_string():
#     return datetime.now().strftime('%Y-%m')


# async def draw_headers(bot: interactions.Client, server_id, clan_settings, total_loot, bg_img, draw):
#     current_month = datetime.now().month
#     month_string = calendar.month_name[current_month].lower()
#     current_year_month = datetime.now().strftime('%Y-%m')
#     this_month = format_gp(total_loot)
#     # recents = f"Recent Submissions"
#     if int(server_id) == 1172737525069135962:
#         title = f"Tracked Drops - All Players ({month_string.capitalize()}) - {this_month}"
#     else:
#         server = bot.get_guild(server_id)
#         server_name = server.name
#         title = f"{server_name}'s Tracked Drops for {month_string.capitalize()} ({this_month})"

#     # Calculate text size using textbbox
#     bbox = draw.textbbox((0, 0), title, font=main_font)
#     text_width = bbox[2] - bbox[0]
#     text_height = bbox[3] - bbox[1]

#     center_header_x = text_width / 2
#     center_header_y = text_height / 2
#     bg_img_w, bg_img_h = bg_img.size
#     center_bg = bg_img_w / 2
#     head_loc_x = int(center_bg - center_header_x)
#     head_loc_y = 20
#     draw.text((head_loc_x, head_loc_y), title, font=main_font, fill=yellow, stroke_width=2, stroke_fill=black)
#     return bg_img


# def load_background_image(filepath):
#     bg_img = Image.open(filepath)
#     draw = ImageDraw.Draw(bg_img)
#     return bg_img, draw


# async def fetch_loot_board_drops(server_id, year_month):
#     # Implementation to fetch drops
#     pass


# def process_drops_data(drops_data, settings):
#     ## drops_data is a direct
#     try:
#         drops_list = {}
#         player_totals = {}
#         recent_drops = []

#         only_show_threshold = settings["only_show_drops_above_threshold_on_lootboard"]
#         minimum_value_to_send_drop = settings["minimum_value_to_send_drop"]
#         eligible_drops = [drop for drop in drops_data["recentDrops"] if
#                           ((int(drop["totalValue"])) > minimum_value_to_send_drop)] if only_show_threshold else [drop
#                                                                                                                  for
#                                                                                                                  drop in
#                                                                                                                  drops_data[
#                                                                                                                      "recentDrops"]]
#         total_loot = 0
#         for drop in eligible_drops:
#             item_name = drop['itemName'].lower().strip()
#             player_name = drop['playerName']
#             quantity = int(drop['quantity'])
#             total_value = int(drop['totalValue'])
#             date_time = drop['dateTime']
#             total_loot += total_value
#             if item_name not in drops_list:
#                 drops_list[item_name] = {'count': 0, 'total_value': 0, 'id': drop['itemId']}
#             drops_list[item_name]['count'] += quantity
#             drops_list[item_name]['total_value'] += total_value

#             if player_name not in player_totals:
#                 player_totals[player_name] = total_value
#             else:
#                 player_totals[player_name] += total_value
#             if int(total_value / quantity) >= int(minimum_value_to_send_drop):
#                 if quantity == 1:
#                     recent_drops.append({"item_name": item_name, "user": player_name, "date": date_time})
#             #elif int(total_value) > 500000:
#                 # print("Didn't add drop because tot/quant = " + str(total_value / quantity))
#         recent_drops = sorted(recent_drops, key=lambda x: x["date"], reverse=True)
#         return drops_list, player_totals, recent_drops, total_loot

#     except Exception as e:
#         print("Couldn't process_drops: ", e)


# def draw_names_list(drops_list, player_totals):
#     top_players = sorted(player_totals.items(), key=lambda x: x[1], reverse=True)[:12]


# async def draw_leaderboard(bg_img, draw, player_totals):
#     top_players = sorted(player_totals.items(), key=lambda x: x[1], reverse=True)[:12]
#     first_name = True
#     name_x = 141
#     name_y = 228
#     pet_font = ImageFont.truetype(rs_font_path, 15)

#     for i, (player, total) in enumerate(top_players):
#         total_player_loot = format_gp(total)
#         rank_num_text = f'{i + 1}'
#         rsn_text = f'{player}'
#         gp_text = f'{total_player_loot}'

#         rank_x, rank_y = (name_x - 104), name_y
#         quant_x, quant_y = (name_x + 106), name_y

#         quant_bbox = draw.textbbox((0, 0), gp_text, font=pet_font)
#         quant_w = quant_bbox[2] - quant_bbox[0]
#         quant_h = quant_bbox[3] - quant_bbox[1]

#         center_q_x = quant_x - quant_w / 2

#         rsn_bbox = draw.textbbox((0, 0), rsn_text, font=pet_font)
#         text_width = rsn_bbox[2] - rsn_bbox[0]
#         text_height = rsn_bbox[3] - rsn_bbox[1]

#         center_x = name_x - text_width / 2

#         rank_bbox = draw.textbbox((0, 0), rank_num_text, font=pet_font)
#         rank_w = rank_bbox[2] - rank_bbox[0]
#         rank_h = rank_bbox[3] - rank_bbox[1]

#         rank_mid_x = rank_x - rank_w / 2

#         draw.text((center_x, name_y), rsn_text, font=pet_font, fill=yellow)
#         draw.text((rank_mid_x, rank_y), rank_num_text, font=pet_font, fill=yellow)
#         draw.text((center_q_x, quant_y), gp_text, font=pet_font, fill=yellow)

#         if not first_name:
#             name_y += 22
#         else:
#             name_y += 22
#             first_name = False

#     return bg_img


# async def draw_drops_on_image(bg_img, draw, drops_list):
#     locations = {}
#     recent_locations = {}
#     small_font = ImageFont.truetype(rs_font_path, 18)
#     amt_font = ImageFont.truetype(rs_font_path, 25)
#     with open("data/item-mapping.csv", 'r') as csvfile:
#         reader = csv.DictReader(csvfile)
#         for i, row in enumerate(reader):
#             locations[i] = row

#     sorted_items = sorted(drops_list.items(), key=lambda x: x[1]['total_value'], reverse=True)[:32]
#     for i, item in enumerate(sorted_items):
#         item_name, item_info = item
#         value = int(item_info['total_value'])
#         current_pos_x = int(locations[i]['x'])
#         current_pos_y = int(locations[i]['y'])
#         img_coords = (current_pos_x - 5, current_pos_y - 12)
#         item_id = item_info['id']
#         if int(item_id) == 995:
#             item_img = await load_image_from_id(1004)
#         elif int(item_id) == 12934:
#             item_img = await load_image_from_id(3999)
#         else:
#             item_img = await load_image_from_id(item_id)
#         if not item_img:
#             try:
#                 item_img = await load_rl_cache_img(item_id)
#             except Exception as e:
#                 continue
#         current_width, current_height = item_img.size
#         scale_factor = 1.6  # resize the image 1.6x
#         new_width, new_height = round(current_width * scale_factor), round(current_height * scale_factor)
#         item_img_resized = item_img.resize((new_width, new_height), Image.Resampling.LANCZOS)  # Corrected this line
#         fixed_img = center_image(item_img_resized, 75, 75)
#         bg_img.paste(fixed_img, img_coords, fixed_img)
#         quantity = item_info['count']
#         if 1000 < quantity < 1000000:
#             quantity_str = str(int(quantity / 1000)) + "K"
#         elif int(quantity / 1000000):
#             quantity_str = str(int(quantity / 1000000)) + "M"
#         else:
#             quantity_str = f"{quantity}"
#         amt_text = quantity_str
#         # Center the text for the total value
#         ctr_x = (current_pos_x + 1)
#         ctr_y = (current_pos_y - 10)
#         num_x, num_y = ctr_x, ctr_y + 45
#         price = format_gp(value)
#         letter = ""
#         if "." in price:
#             if "B" not in price:
#                 price, dec = price.split(".")
#                 if "K" in dec:
#                     letter = "K"
#                 else:
#                     letter = "M"
#                 # temporary value placeholder
#                 if letter == "":
#                     letter = "GP"
#             price = f'{price}{letter}'
#         draw.text((num_x, num_y), price, font=small_font, fill=yellow, stroke_width=1, stroke_fill=black)
#         # Counter
#         draw.text((ctr_x, ctr_y), amt_text, font=amt_font, fill=yellow, stroke_width=2, stroke_fill=black)
#     return bg_img


# async def draw_recent_drops(bg_img, draw, recent_drops):
#     print("Recent drops:", recent_drops)
#     sorted_recents = sorted(recent_drops, key=lambda x: x['date'], reverse=True)
#     most_recents = sorted_recents[:12]
#     small_font = ImageFont.truetype(rs_font_path, 18)
#     recent_locations = {}
#     with open("data/recent-mapping.csv", 'r') as csvfile:
#         reader = csv.DictReader(csvfile)
#         for i, row in enumerate(reader):
#             recent_locations[i] = row
#     for i, data in enumerate(sorted_recents[:12]):
#         item = data["item_name"]
#         username = data["user"]
#         date_obj = datetime.strptime(data["date"], '%Y-%m-%dT%H:%M:%S.%fZ')
#         item_name = item.lower()
#         current_pos_x = int(recent_locations[i]['x'])
#         current_pos_y = int(recent_locations[i]['y'])
#         item_id = items.find_item_id(item_name)
#         item_img = await load_image_from_id(item_id)
#         if not item_img:
#             continue
#         scale_factor = 1.8
#         current_width, current_height = item_img.size
#         new_width = round(current_width * scale_factor)
#         new_height = round(current_height * scale_factor)
#         item_img_resized = item_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
#         fixed_item_img = center_image(item_img_resized, 75, 75)
#         img_coords = (current_pos_x - 5, current_pos_y - 12)
#         bg_img.paste(fixed_item_img, img_coords, fixed_item_img)
#         center_x = (current_pos_x + 1)
#         center_y = (current_pos_y - 10)
#         name_x, name_y = center_x + 5, center_y
#         current_time = datetime.now()
#         time_since = current_time - date_obj
#         seconds = time_since.total_seconds()
#         minutes = seconds // 60
#         hours = minutes // 60
#         days = hours // 24
#         # Remainder hours after subtracting the days
#         hours %= 24
#         # Remainder minutes after subtracting the hours
#         minutes %= 60
#         time_font = ImageFont.truetype(rs_font_path, 15)
#         item_text = f'{username}'
#         if int(days) > 0:
#             time_since_disp = f"({int(days)}d{int(hours)}hr)"
#         else:
#             if int(hours) > 0:
#                 time_since_disp = f"({int(hours)}h{int(minutes)}min)"
#             else:
#                 if minutes > 1:
#                     time_since_disp = f"({int(minutes)}mins)"
#                 else:
#                     time_since_disp = f"(1 min)"
#         t_sl_x = current_pos_x
#         t_sl_y = (current_pos_y + 35)
#         bbox_username = draw.textbbox((name_x, name_y), username, font=small_font)
#         bbox_time_since = draw.textbbox((t_sl_x, t_sl_y), time_since_disp, font=time_font)

#         draw.text((name_x, name_y), username, font=small_font, fill=yellow, stroke_width=1, stroke_fill=black)
#         t_sl_x = current_pos_x
#         t_sl_y = (current_pos_y + 35)
#         draw.text((t_sl_x, t_sl_y), time_since_disp, font=time_font, fill=yellow)

#     return bg_img


# def center_image(image, width, height):
#     # Create a new image with the desired dimensions and a transparent background
#     centered_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
#     # Calculate the position where the original image should be pasted to be centered
#     paste_x = (width - image.width) // 2
#     paste_y = (height - image.height) // 2
#     # Paste the original image onto the new image at the calculated position
#     centered_image.paste(image, (paste_x, paste_y))
#     return centered_image


# def save_image(image, server_id):
#     # Save logic here
#     os.makedirs(f"M:\\droptracker-react\\droptracker-react\\public\\assets\\img\\clan\\{server_id}", exist_ok=True)
#     image.save(f"M:\\droptracker-react\\droptracker-react\\public\\assets\\img\\clan\\{server_id}\\loot_board.png")
#     # image.save(f'data/{server_id}/loot-board.png')


# async def load_image_from_id(item_id):
#     if item_id == "None" or item_id is None or not isinstance(item_id, int):
#         return None
#     file_path = f"M:\\droptracker-react\\droptracker-react\\public\\assets\\img\\itemdb\\{item_id}.png"
#     loop = asyncio.get_event_loop()
#     try:
#         # Run the blocking Image.open operation in a thread pool
#         image = await loop.run_in_executor(None, Image.open, file_path)
#         return image
#     except Exception as e:
#         print(f"The following file path: {file_path} produced an error: {e}")
#         return None


# async def load_rl_cache_img(item_id):
#     url = f"https://static.runelite.net/cache/item/icon/{item_id}.png"
#     try:
#         ## save it here
#         async with aiohttp.ClientSession() as session:
#             async with session.get(url) as response:
#                 # Ensure the request was successful
#                 if response.status != 200:
#                     print(f"Failed to fetch image for item ID {item_id}. HTTP status: {response.status}")
#                     return None

#                 # Read the response content
#                 image_data = await response.read()

#                 # Load the image data into a PIL Image object
#                 image = Image.open(BytesIO(image_data))
#                 file_path = f"M:\\droptracker-react\\droptracker-react\\src\\assets\\img\\itemdb\\{item_id}.png"
#                 # print("Saving")
#                 image.save(file_path, "PNG")
#                 return image

#     except Exception as e:
#         print("Unable to load the item.")
#     finally:
#         await aiohttp.ClientSession().close()
