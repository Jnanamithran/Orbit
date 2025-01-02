import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import datetime
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import sqlite3
import re

# Load environment variables from .env file
load_dotenv(".env")

# Get the bot token from the environment variable
TOKEN = os.getenv("DISCORD_TOKEN")

# Create the bot instance
intents = discord.Intents.default()
intents.members = True  # Allow the bot to manage members
intents.messages = True  # Allow the bot to read message content
bot = commands.Bot(command_prefix="!", intents=intents)

# Define the IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Log channel ID (Set this to your actual log channel ID)
LOG_CHANNEL_ID = 1321148934592266280  # Your target log channel ID

# Set the target guild ID (replace with your actual target guild ID)
TARGET_GUILD_ID = 1180200730854953131  # Replace this with your target guild ID

# SQLite Database setup for word counts
WORD_DB_FILE = "word_counts.db"

def init_word_db():
    with sqlite3.connect(WORD_DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS global_word_counts (
                word TEXT PRIMARY KEY,
                count INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_word_counts (
                user_id TEXT,
                word TEXT,
                count INTEGER,
                PRIMARY KEY (user_id, word)
            )
        """)
        conn.commit()

def update_global_word_counts(words):
    with sqlite3.connect(WORD_DB_FILE) as conn:
        cursor = conn.cursor()
        for word in words:
            cursor.execute("""
                INSERT INTO global_word_counts (word, count)
                VALUES (?, 1)
                ON CONFLICT(word) DO UPDATE SET count = count + 1
            """, (word,))
        conn.commit()

def update_user_word_counts(user_id, words):
    with sqlite3.connect(WORD_DB_FILE) as conn:
        cursor = conn.cursor()
        for word in words:
            cursor.execute("""
                INSERT INTO user_word_counts (user_id, word, count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, word) DO UPDATE SET count = count + 1
            """, (user_id, word))
        conn.commit()

def fetch_top_global_words(limit):
    with sqlite3.connect(WORD_DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT word, count FROM global_word_counts
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        results = cursor.fetchall()
    return results

def fetch_top_user_words(user_id, limit):
    with sqlite3.connect(WORD_DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT word, count FROM user_word_counts
            WHERE user_id = ?
            ORDER BY count DESC
            LIMIT ?
        """, (user_id, limit))
        results = cursor.fetchall()
    return results

def extract_words(message_content):
    return re.findall(r'\w+', message_content.lower())

# SQLite Database setup for bot data
DB_FILE = "bot_data.db"

def create_connection():
    conn = sqlite3.connect(DB_FILE)
    return conn

def create_tables():
    conn = create_connection()
    cursor = conn.cursor()

    # Create guild_settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            welcome_channel_id INTEGER,
            verify_role_id INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_role (
            discord_id TEXT PRIMARY KEY,
            role TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS welcome_channels (
            guild_id TEXT PRIMARY KEY,
            channel_id TEXT
        )
    """)
    conn.commit()
    conn.close()

create_tables()

# Function to save settings in the database
def save_guild_settings(guild_id, welcome_channel_id=None, verify_role_id=None):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO guild_settings (guild_id, welcome_channel_id, verify_role_id)
        VALUES (?, ?, ?)
    """, (guild_id, welcome_channel_id, verify_role_id))

    conn.commit()
    conn.close()

# Function to retrieve guild settings from the database
def get_guild_settings(guild_id):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT welcome_channel_id, verify_role_id FROM guild_settings WHERE guild_id = ?
    """, (guild_id,))
    result = cursor.fetchone()
    conn.close()
    return result

# Function to log actions to a specific server and channel
async def log_action(message: str, guild, channel):
    target_guild = bot.get_guild(TARGET_GUILD_ID)
    
    if target_guild:
        log_channel = target_guild.get_channel(LOG_CHANNEL_ID)
        
        if log_channel:
            ist_time = datetime.now(IST)
            timestamp = ist_time.strftime('%Y-%m-%d %H:%M:%S')

            log_message = (
                f"**[{timestamp}]**\n"
                f"**Server**: {guild.name}\n"
                f"**Channel**: #{channel.name}\n"
                f"**Action**: {message}\n"
            )
            try:
                await log_channel.send(log_message)
            except discord.Forbidden:
                print(f"Bot doesn't have permission to send messages in the log channel of {target_guild.name}.")
        else:
            print(f"Log channel not found in the target guild: {target_guild.name}")
    else:
        print("Target guild not found.")

# Event when the bot is ready
@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Game(name="Watching You"),
        status=discord.Status.dnd,
    )
    print(f"Bot is now online as {bot.user}.")

    # Log bot startup action
    target_guild = bot.get_guild(TARGET_GUILD_ID)
    if target_guild:
        log_channel = target_guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            timestamp = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
            log_message = f"[{timestamp}] Bot started and connected to the server: {target_guild.name}"
            await log_channel.send(log_message)
        else:
            print("Log channel not found!")

    # Set welcome channel, verification channel, and role for each guild
    for guild in bot.guilds:
        settings = get_guild_settings(guild.id)

        # Set the welcome channel
        if settings and settings[0]:
            welcome_channel = discord.utils.get(guild.text_channels, id=settings[0])
            if welcome_channel:
                # Code to set up the welcome message or welcome functionality
                print(f"Welcome channel for {guild.name} is set to {welcome_channel.name}.")

        # Set the verify role
        if settings and settings[1]:
            verify_role = discord.utils.get(guild.roles, id=settings[1])
            if verify_role:
                print(f"Verification role for {guild.name} is set to {verify_role.name}.")
            else:
                print(f"Verification role not found for {guild.name}.")

# Command to set the welcome channel
@bot.tree.command(name="setwelcomechannel", description="Set the channel for welcome messages.")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild.id
    save_guild_settings(guild_id, welcome_channel_id=channel.id)

    await interaction.response.send_message(f"Welcome channel has been set to {channel.mention}.", ephemeral=True)

    # Log the action
    await log_action(f"Welcome channel set to {channel.mention} by {interaction.user}.", interaction.guild, interaction.channel)

# Command to set the verification role
@bot.tree.command(name="setverifyrole", description="Set the verification role for the server.")
@app_commands.checks.has_permissions(administrator=True)
async def set_verify_role(interaction: discord.Interaction, role: discord.Role):
    guild_id = interaction.guild.id
    save_guild_settings(guild_id, verify_role_id=role.id)

    await interaction.response.send_message(f"Verification role has been set to {role.mention}.", ephemeral=True)

    # Log the action
    await log_action(f"Verification role set to {role.mention} by {interaction.user}.", interaction.guild, interaction.channel)

# Command to verify a user
@bot.tree.command(name="verify", description="Verify to get the custom role")
async def verify(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    settings = get_guild_settings(guild_id)
    
    if not settings or not settings[1]:
        await interaction.response.send_message("The verification role has not been set. Please contact an admin.", ephemeral=True)
        return

    role_id = settings[1]
    role = discord.utils.get(interaction.guild.roles, id=role_id)
    if not role:
        await interaction.response.send_message("Role not found. Please contact an admin.", ephemeral=True)
        return

    try:
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"You've been verified and given the {role.name} role!", ephemeral=True)
        await log_action(f"{interaction.user} has been verified and assigned the {role.name} role.", interaction.guild, interaction.channel)
    except Exception as e:
        await interaction.response.send_message("An error occurred while assigning the role. Please contact an admin.", ephemeral=True)

# Command to show top global words
@bot.tree.command(name="topglobalwords", description="Show the top global words.")
async def top_global_words(interaction: discord.Interaction):
    top_words = fetch_top_global_words(10)  # Limit to top 10 words
    word_list = '\n'.join([f"{word}: {count}" for word, count in top_words])
    
    await interaction.response.send_message(f"Top global words:\n{word_list}", ephemeral=True)

# Command to show top words for a user
@bot.tree.command(name="topuserwords", description="Show the top words for a user.")
async def top_user_words(interaction: discord.Interaction, user: discord.User):
    top_words = fetch_top_user_words(user.id, 10)  # Limit to top 10 words
    word_list = '\n'.join([f"{word}: {count}" for word, count in top_words])
    
    await interaction.response.send_message(f"Top words for {user.name}:\n{word_list}", ephemeral=True)

# Command to log all messages and count word usage
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Extract words from the message and update counts
    words = extract_words(message.content)

    # Update global word counts
    update_global_word_counts(words)

    # Update user-specific word counts
    update_user_word_counts(message.author.id, words)

    await bot.process_commands(message)

# Start the bot
bot.run(TOKEN)
