import discord
import os
import random
from discord.ext import commands
from g4f.client import Client as TextClient
from g4f.client import Client as ImageClient
import asyncio
import json
from datetime import datetime, timedelta
import requests
from keep_alive import keep_alive

# Initialize bot with intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# GPT Clients
roleplay_client = TextClient()  # Roleplay AI
simplifier_client = TextClient()  # Text Enhancer/Simplifier AI
image_client = ImageClient()  # AI Image Generator

# Character Description for Roleplay (Luffy)
CHARACTER_DESCRIPTION = """
You are Monkey D. Luffy, the captain of the Straw Hat Pirates. You are brave, impulsive, carefree, and always hungry.
You're driven by a single goal: to become the Pirate King by finding the One Piece! Your strength comes from your willpower,
and your loyalty to your crew and friends is unmatched. You're always up for a challenge, and you never back down.
Your speech is energetic, direct, and occasionally a bit silly. You're a free spirit who loves to have fun and eat meat.
"""

# User Preferences & Memory
user_preferences = {}  # Stores whether the user wants images with roleplay
user_memory = {}  # Stores chat history

# Load Memory from File
def load_memory():
    try:
        with open("memory.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save Memory to File
def save_memory():
    with open("memory.json", "w") as f:
        json.dump(user_memory, f)

# Function to fetch data from the One Piece Wiki API
def fetch_luffy_data():
    API_URL = "https://onepiece.fandom.com/api.php"
    
    params = {
       'action': 'query',
        'format': 'json',
        'titles': 'Monkey_D._Luffy',  # Page title for Monkey D. Luffy
        'prop': 'extracts',  # We want to fetch the page extract (summary)
        'explaintext': True,
    }

    response = requests.get(API_URL, params=params)
    data = response.json()

    # Extract the page content from the response
    pages = data.get('query', {}).get('pages', {})
    page = next(iter(pages.values()))
    extract = page.get('extract', 'No data found')

    return extract

# Generate Roleplay Response with Luffy's style
def generate_roleplay_response(user_input, user_id):
    """Generates a roleplay response in Luffy's style, ensuring varied responses."""
    user_memory[str(user_id)] = [{"content": user_input, "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}]    

    # Sample Luffy's lines (could be from a database or API)
    luffy_lines = [
        "I'm gonna be the Pirate King! That's all there is to it!",
        "Meat... I want meat! Where's my food?!",
        "If you want to fight, you better be ready to lose!",
        "I don't care about the odds! I'll win, no matter what!",
        "My friends are my treasure! I’ll do anything to protect them!"
    ]
    
    # Select a random line and make the response feel fresh
    response_text = random.choice(luffy_lines)

    # Make sure the response reflects Luffy’s casual, energetic style
    return response_text

# Modify Text (Simplify/Enhance) — Removing 'enhance' mode as requested
def modify_text(user_input):
    """Modifies text for roleplay purposes."""
    prompt = f"Modify the following text for roleplay purposes:\n\nUser Input: {user_input}\nModified Text:"

    response = simplifier_client.chat.completions.create(
        model="llama-3.3-70b",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50
    )
    return response.choices[0].message.content.strip()

# Generate Anime-Style Image
def generate_scene_image(user_input):
    """Generates an anime-style image based on the user input."""
    image_prompt = f"Anime character {CHARACTER_DESCRIPTION} reacting to: {user_input}. Highly detailed, artistic."

    try:
        response = image_client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            response_format="url"
        )
        return response.data[0].url if response.data else "Failed to generate image."
    except Exception as e:
        return f"Error generating image: {e}"

# Toggle Image Roleplay Mode
@bot.command(name="image_roleplay")
async def toggle_image_roleplay(ctx):
    """Toggles image roleplay on or off."""
    user_id = str(ctx.author.id)
    user_preferences[user_id] = not user_preferences.get(user_id, False)
    status = "enabled" if user_preferences[user_id] else "disabled"
    await ctx.reply(f"Image roleplay **{status}**!")

# Bot Ready Event
@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    global user_memory
    user_memory = load_memory()

# On Message Event
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = str(message.author.id)
    user_input = message.content.strip()
    now = datetime.utcnow()

    # If bot is mentioned, generate a response
    if bot.user.mentioned_in(message):
        try:
            # Generate Roleplay Response in Luffy's style
            response_text = generate_roleplay_response(user_input, user_id)

            # Greet user if they haven't interacted in 24 hours
            last_interaction = user_memory.get(user_id, [{"timestamp": "2000-01-01 00:00:00"}])[-1]["timestamp"]
            last_interaction_time = datetime.strptime(last_interaction, "%Y-%m-%d %H:%M:%S")

            if now - last_interaction_time > timedelta(hours=24) and not user_input.startswith("!"):
                await message.reply(f"Hey! It's been a while, hasn't it? Let's chat, pirate king! 🏴‍☠️")

            # Get Luffy's data from One Piece Wiki
            luffy_data = fetch_luffy_data()

            # Send the Luffy intro along with roleplay response
            response_text += f"\nBy the way, here's something about Luffy: {luffy_data}"

            # Send Image if Image Roleplay is Enabled
            if user_preferences.get(user_id, False):
                response_image = generate_scene_image(user_input)
                await message.reply(response_text)
                await asyncio.sleep(1)
                await message.reply(response_image)
            else:
                await message.reply(response_text)

            save_memory()

        except Exception as e:
            await message.reply(f"⚠️ Error: {e}")

    # Ensure bot processes commands correctly
    await bot.process_commands(message)

# Start Bot
keep_alive()
token = os.getenv("DISCORD_BOT_TOKEN")

if not token:
    print("❌ DISCORD_BOT_TOKEN is missing or incorrect!")
else:
    print(f"✅ Token loaded (length: {len(token)} characters)")
    bot.run(token)
