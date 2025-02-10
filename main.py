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

# Generate Roleplay Response with Context Awareness
def generate_roleplay_response(user_input, user_id):
    """Generates a roleplay response considering previous conversations."""
    if user_id not in user_memory:
        user_memory[user_id] = []
    
    user_memory[user_id].append({"content": user_input, "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")})

    # Get previous interactions for context
    context = "\n".join([f"User: {entry['content']}" for entry in user_memory[user_id][-5:]])  # Limit context to last 5 messages
    full_prompt = f"{CHARACTER_DESCRIPTION}\n\n{context}\nTana:"

    response = roleplay_client.chat.completions.create(
        model="llama-3.3-70b",
        messages=[{"role": "user", "content": full_prompt}],
        max_tokens=150
    )

    response_text = response.choices[0].message.content.strip()
    return response_text

# Generate Anime-Style Image
def generate_scene_image(user_input):
    """Generates an anime-style image based on user input."""
    image_prompt = f"Anime girl, {CHARACTER_DESCRIPTION} reacting to: {user_input}. Highly detailed, artistic."

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
            # Generate Roleplay Response with Context Awareness
            response_text = generate_roleplay_response(user_input, user_id)

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
