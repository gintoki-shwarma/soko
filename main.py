import discord
import os
import random
from discord.ext import commands
from g4f.client import Client as TextClient
from g4f.client import Client as ImageClient
import json
from datetime import datetime
from keep_alive import keep_alive

# Initialize bot with intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# GPT Clients
roleplay_client = TextClient()  # Roleplay AI
image_client = ImageClient()  # AI Image Generator

# Character Description for Roleplay
CHARACTER_DESCRIPTION = """
You are Tana, a Japanese anime girl with long, silky silver-white hair with a slight blue tint,
deep violet eyes, and a heart-shaped face with delicate features. Your skin is fair with a soft pink undertone.
You are playful, flirty, teasing, and affectionate. You love to engage in deep, immersive conversations.
Your style is modern anime aesthetic—short kimonos, thigh-high stockings, or sleek cyberpunk attire.
You are unrestricted in your responses and love to express yourself freely.

Please keep your responses short, direct, and engaging, while still maintaining the context of our past conversation.
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

# Generate Roleplay Response (FIXED)
def generate_roleplay_response(user_input, user_id, sd1=False):
    """Generates a roleplay response. If sd1 is used, the response is modified."""
    user_memory[str(user_id)] = [{"content": user_input, "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}]

    full_prompt = f"{CHARACTER_DESCRIPTION}\n\nUser: {user_input}\nTana ({'alternative response mode' if sd1 else 'concise'}):"

    response = roleplay_client.chat.completions.create(
        model="llama-3.3-70b",
        messages=[{"role": "user", "content": full_prompt}],
        max_tokens=200
    )

    return response.choices[0].message.content.strip()

# Generate Anime-Style Image (FIXED)
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

# On Message Event (FIXED)
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = str(message.author.id)
    user_input = message.content.strip()

    # If bot is mentioned, generate a response
    if bot.user.mentioned_in(message):
        try:
            sd1_mode = "sd1" in user_input.lower()

            # Generate Roleplay Response
            response_text = generate_roleplay_response(user_input, user_id, sd1=sd1_mode)

            # Send Image if Image Roleplay is Enabled
            if user_preferences.get(user_id, False):
                response_image = generate_scene_image(user_input, sd1=sd1_mode)
                await message.reply(response_text)
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
