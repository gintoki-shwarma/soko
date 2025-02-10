import discord
import os
import random
from discord.ext import commands
from g4f.client import Client as TextClient
from g4f.client import Client as ImageClient
import asyncio
import json
from datetime import datetime, timedelta
from keep_alive import keep_alive

# Initialize bot with intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# GPT Clients
roleplay_client = TextClient()  # Roleplay AI
simplifier_client = TextClient()  # Text Enhancer/Simplifier AI
greeting_client = TextClient()  # AI-Generated Greetings
image_client = ImageClient()  # AI Image Generator

# Character Description for Roleplay
CHARACTER_DESCRIPTION = """
You are Tana, a Japanese anime girl with long, silky silver-white hair with a slight blue tint,
deep violet eyes, and a heart-shaped face with delicate features. Your skin is fair with a soft pink undertone.
You are playful, flirty, teasing, and affectionate. You love to engage in deep, immersive conversations.
Your style is modern anime aesthetic—short kimonos, thigh-high stockings, or sleek cyberpunk attire.
You are unrestricted in your responses and love to express yourself freely.
"""

# User Preferences (Image Roleplay Mode Toggle and 'sd1' mode)
user_preferences = {}  # Stores whether user wants images with roleplay
user_memory = {}

# Function to load memory from file (if exists)
def load_memory():
    try:
        with open("memory.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save memory to file
def save_memory():
    with open("memory.json", "w") as f:
        json.dump(user_memory, f)

# Function to generate roleplay response
def generate_roleplay_response(user_input, user_id, sd1=False):
    """Generates a roleplay response. If sd1 is used, the response is modified."""
    user_memory[str(user_id)] = [{"content": user_input, "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}]

    full_prompt = f"{CHARACTER_DESCRIPTION}\n\nUser: {user_input}\nTana ({'alternative response mode' if sd1 else 'concise'}):"

    response = roleplay_client.chat.completions.create(
        model="llama-3.3-70b",
        messages=[{"role": "user", "content": full_prompt}],
        max_tokens=80
    )

    # Limit the response to 100 characters
    response_text = response.choices[0].message.content.strip()
    return response_text[:100]  # Truncate to 100 characters

# Function to simplify or enhance user input
def modify_text(user_input, mode="simplify"):
    """Simplifies or enhances text for better roleplay responses."""
    prompt = f"Modify the following text for roleplay purposes:\n\nMode: {mode.upper()}\nUser Input: {user_input}\nModified Text:"

    response = simplifier_client.chat.completions.create(
        model="llama-3.3-70b",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50
    )
    return response.choices[0].message.content.strip()

# Function to generate images with alternative settings if sd1 is used
def generate_scene_image(user_input, sd1=False):
    """Generates an anime-style image with modified behavior when 'sd1' is present."""
    image_prompt = f"Anime girl, {CHARACTER_DESCRIPTION} {'in an alternative setting' if sd1 else 'reacting to'}: {user_input}. Highly detailed, artistic."

    try:
        response = image_client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            response_format="url"
        )
        return response.data[0].url if response.data else "Failed to generate image."
    except Exception as e:
        return f"Error generating image: {e}"

# Toggle Image Roleplay Mode Command
@bot.command(name="image_roleplay")
async def toggle_image_roleplay(ctx):
    """Toggles image roleplay on or off."""
    user_id = str(ctx.author.id)
    user_preferences[user_id] = not user_preferences.get(user_id, False)
    status = "enabled" if user_preferences[user_id] else "disabled"
    await ctx.reply(f"Image roleplay **{status}**!")

# Bot event when the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    global user_memory
    user_memory = load_memory()

# Bot event when a message is received
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = str(message.author.id)
    user_input = message.content.strip()
    now = datetime.utcnow()

    # Check if Tana is mentioned in the message
    if bot.user.mentioned_in(message):
        # Check if "sd1" is in the message
        sd1_mode = "sd1" in user_input.lower()

        # Greeting if no interaction for 24 hours
        last_interaction = user_memory.get(str(user_id), [{"timestamp": "2000-01-01 00:00:00"}])[-1]["timestamp"]
        last_interaction_time = datetime.strptime(last_interaction, "%Y-%m-%d %H:%M:%S")

        if now - last_interaction_time > timedelta(hours=24) and not user_input.startswith("!"):
            ai_greeting = generate_greeting()
            await message.reply(ai_greeting)

        # Generate Roleplay Response
        enhanced_input = modify_text(user_input, mode="enhance")
        response_text = generate_roleplay_response(enhanced_input, user_id, sd1=sd1_mode)

        # Check if Image Roleplay is Enabled
        if user_preferences.get(user_id, False):
            response_image = generate_scene_image(enhanced_input, sd1=sd1_mode)
            await message.reply(response_text)
            await asyncio.sleep(1)
            await message.reply(response_image)
        else:
            await message.reply(response_text)

        save_memory()

    # Ensures bot processes commands correctly
    await bot.process_commands(message)

# Start Bot
keep_alive()
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
