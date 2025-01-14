import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import asyncio
import datetime
from datetime import datetime, timedelta
import sqlite3
import pytz
from dotenv import load_dotenv
from contextlib import contextmanager
# Load environment variables from .env file
load_dotenv(".env")

# Get the bot token from the environment variable
TOKEN = os.getenv("DISCORD_TOKEN")

# Create the bot instance
intents = discord.Intents.default()
intents.members = True  # Allow the bot to manage members
bot = commands.Bot(command_prefix="!", intents=intents)

# A dictionary to store channel and role IDs for each guild
guild_settings = {}

# Log channel ID (Set this to your actual log channel ID)
LOG_CHANNEL_ID = 1321148934592266280  # Your target log channel ID

# Set the target guild ID (replace with your actual target guild ID)
TARGET_GUILD_ID = 1180200730854953131  # Replace this with your target guild ID

# Define the IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Dictionary to store the welcome channel settings (in memory)
welcome_channels = {}

# Connect to the database
conn = sqlite3.connect('your_database.db')
c = conn.cursor()

# List all tables to verify the table name
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = c.fetchall()
print("Tables in database:", tables)

# Check if your table exists (replace 'your_table_name' with the actual table name)
if ('your_table_name',) in tables:
    c.execute('''ALTER TABLE your_table_name ADD COLUMN log_channel_id INTEGER;''')
else:
    print("Table 'your_table_name' does not exist.")

# Commit changes and close the connection
conn.commit()
conn.close()

@contextmanager
def db_connection():
    conn = sqlite3.connect('bot_data.db')
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def init_db():
    with db_connection() as conn:
        c = conn.cursor()

        # Create the settings table if it doesn't exist
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
                        guild_id INTEGER PRIMARY KEY,
                        welcome_channel_id INTEGER,
                        verify_channel_id INTEGER,
                        verify_role_id INTEGER,
                        log_channel_id INTEGER)''')
        
        # Check if 'log_channel_id' exists
        c.execute("PRAGMA table_info(settings);")
        columns = [column[1] for column in c.fetchall()]
        
        # Add the column if it doesn't exist
        if 'log_channel_id' not in columns:
            try:
                c.execute('ALTER TABLE settings ADD COLUMN log_channel_id INTEGER;')
                print("log_channel_id column added.")
            except sqlite3.OperationalError as e:
                print(f"Error adding column: {e}")

        # Create the activity_settings table if it doesn't exist
        c.execute('''CREATE TABLE IF NOT EXISTS activity_settings (
                        guild_id INTEGER PRIMARY KEY,
                        activity_type TEXT,
                        activity_name TEXT,
                        stream_url TEXT)''')
        
        conn.commit()


    
# Function to set guild settings (welcome channel, verify channel, verify role)
def set_guild_settings(guild_id, welcome_channel_id, verify_channel_id, verify_role_id):
    print(f"Saving settings: guild_id={guild_id}, welcome_channel_id={welcome_channel_id}, verify_channel_id={verify_channel_id}, verify_role_id={verify_role_id}")
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO settings (guild_id, welcome_channel_id, verify_channel_id, verify_role_id)
        VALUES (?, ?, ?, ?)
    ''', (guild_id, welcome_channel_id, verify_channel_id, verify_role_id))
    conn.commit()
    conn.close()

# Function to get guild settings
def get_guild_settings(guild_id):
    print(f"Fetching settings for guild_id={guild_id}")
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('SELECT * FROM settings WHERE guild_id = ?', (guild_id,))
    settings = c.fetchone()
    print(f"Retrieved settings: {settings}")
    conn.close()
    return settings

# Function to log actions to a specific server (global log for bot owner and guild-specific logs)
async def log_action(message: str, guild, channel, is_guild_owner_log=False):
    # Global log for bot owner
    target_guild = bot.get_guild(TARGET_GUILD_ID)
    
    if target_guild:
        log_channel = target_guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            ist_time = datetime.now(IST)
            timestamp = ist_time.strftime('%Y-%m-%d %H:%M:%S')
            embed = discord.Embed(title="Log Entry", color=discord.Color.red(), timestamp=ist_time)
            embed.add_field(name="Server", value=guild.name, inline=False)
            embed.add_field(name="Channel", value=f"#{channel.name}", inline=False)
            embed.add_field(name="Action", value=message, inline=False)
            embed.set_footer(text="Logged at")

            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                print(f"Bot doesn't have permission to send messages in the log channel of {target_guild.name}.")

    # Guild owner-specific log
    if is_guild_owner_log:
        guild_owner = guild.owner  # Get the guild owner
        if guild_owner:
            # You can create a log channel for each guild if it's not already set, or fetch it from the database
            log_channel = guild.get_channel(guild.owner.id)  # Assuming the owner has a private log channel set
            if log_channel:
                embed = discord.Embed(title="Guild Specific Log", color=discord.Color.blue(), timestamp=ist_time)
                embed.add_field(name="Server", value=guild.name, inline=False)
                embed.add_field(name="Channel", value=f"#{channel.name}", inline=False)
                embed.add_field(name="Action", value=message, inline=False)
                embed.set_footer(text="Logged for the guild owner")

                try:
                    await guild_owner.send(embed=embed)  # Send the log directly to the guild owner
                except discord.Forbidden:
                    print(f"Unable to send guild-specific log to the owner of {guild.name}.")



@bot.event
async def on_ready():
    init_db()

    try:
        # Sync commands
        await bot.tree.sync()
        print(f"Logged in as {bot.user} and synced commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    # Set bot's initial status
    await bot.change_presence(
        activity=discord.Game(name="Commands: !help"),
        status=discord.Status.dnd,
    )
    # Fetch activity settings from the database and set the bot's status
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('SELECT guild_id, activity_type, activity_name, stream_url FROM activity_settings')
    rows = c.fetchall()
    for row in rows:
        guild_id, activity_type, activity_name, stream_url = row
        guild = bot.get_guild(guild_id)
        if guild:
            if activity_type == "playing":
                activity = discord.Game(name=activity_name)
            elif activity_type == "listening":
                activity = discord.Activity(type=discord.ActivityType.listening, name=activity_name)
            elif activity_type == "watching":
                activity = discord.Activity(type=discord.ActivityType.watching, name=activity_name)
            elif activity_type == "streaming":
                activity = discord.Streaming(name=activity_name, url=stream_url)
            await bot.change_presence(activity=activity)

    # Close the database connection
    conn.close()

    # Log bot startup action to the log channel of the target guild
    startup_message = f"Bot started and connected."
    
    # Loop through all guilds and log the startup message
    for guild in bot.guilds:
        # Fetch the log channel for the guild from the database
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute('SELECT log_channel_id FROM settings WHERE guild_id = ?', (guild.id,))
        result = c.fetchone()
        conn.close()

        if result:
            log_channel_id = result[0]
            log_channel = guild.get_channel(log_channel_id)

            if log_channel:
                await log_action(startup_message, guild, log_channel)
            else:
                print(f"Log channel not found in guild: {guild.name}")
        else:
            print(f"Log channel not set for guild: {guild.name}")



# Command to set log channel
@bot.tree.command(name="setlogchannel", description="Set the channel for logging messages.")
@app_commands.checks.has_permissions(administrator=True)
async def set_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    # Set the log channel for the guild in the database
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO settings (guild_id, log_channel_id) VALUES (?, ?)''', 
              (interaction.guild.id, channel.id))
    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"Log channel has been set to {channel.mention}.", ephemeral=True
    )
    
    # Log the action of setting the log channel
    await log_action(f"Log channel has been set to {channel.mention} by {interaction.user}.", interaction.guild, interaction.channel)

@bot.event
async def on_ready():
    # Set the bot's status to DND
    await bot.change_presence(status=discord.Status.dnd, activity=None)
    print(f'We have logged in as {bot.user}')

@bot.tree.command(name="activity", description="Change the bot's activity")
@app_commands.describe(
    activity_type="The type of activity (playing, listening, watching, streaming)", 
    activity_name="The name of the activity",
    stream_url="The URL for streaming (required for 'streaming' activity)"
)
async def set_activity(interaction: discord.Interaction, activity_type: str, activity_name: str, stream_url: str = None):
    # Check if the user is authorized
    if interaction.user.id != 722036964584587284 :  # Replace with your actual user ID
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return

    activity = None

    if activity_type.lower() == "playing":
        activity = discord.Game(name=activity_name)
    elif activity_type.lower() == "listening":
        activity = discord.Activity(type=discord.ActivityType.listening, name=activity_name)
    elif activity_type.lower() == "watching":
        activity = discord.Activity(type=discord.ActivityType.watching, name=activity_name)
    elif activity_type.lower() == "streaming":
        if not stream_url:
            await interaction.response.send_message("You must provide a streaming URL for the 'streaming' activity type.", ephemeral=True)
            return
        activity = discord.Streaming(name=activity_name, url=stream_url)
    else:
        await interaction.response.send_message("Invalid activity type! Use 'playing', 'listening', 'watching', or 'streaming'.", ephemeral=True)
        return

    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO activity_settings (guild_id, activity_type, activity_name, stream_url) VALUES (?, ?, ?, ?)''', 
              (interaction.guild.id, activity_type, activity_name, stream_url))
    conn.commit()
    conn.close()

    # Set the bot's activity while ensuring the status remains DND
    await bot.change_presence(status=discord.Status.dnd, activity=activity)
    await interaction.response.send_message(f"Bot activity changed to {activity_type} {activity_name}!", ephemeral=True)
    
    # Log the action
    await log_action(f"{interaction.user} changed the bot's activity to {activity_type} {activity_name} in {interaction.guild.name}.", interaction.guild, interaction.channel)

# Event that triggers when a member joins
@bot.event
async def on_member_join(member: discord.Member):
    # Get the welcome channel ID for the server from memory
    channel_id = welcome_channels.get(str(member.guild.id))
    if channel_id:
        welcome_channel = member.guild.get_channel(channel_id)
        if welcome_channel:
            # Send a dynamic welcome message
            await welcome_channel.send(
                f"🌟 Welcome to {member.guild.name}, {member.mention}! 🌟\n"
                "We're glad to have you here! 🎉\n"
                "Enjoy your stay and explore the server!"
            )
            await member.send(f"Welcome {member.mention} to {member.guild.name} \n Have fun in exploring the server \n Any doubt dont frgt to contact admins.👻")
            # Log the action of sending the welcome message
            await log_action(f"Sent welcome message to {member.mention} in {welcome_channel.mention}.", member.guild, welcome_channel)

# Command to set welcome channel
@bot.tree.command(name="setwelcomechannel", description="Set the channel for welcome messages.")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    # Set the channel for the guild in the database
    set_guild_settings(interaction.guild.id, channel.id, None, None)

    await interaction.response.send_message(
        f"Welcome channel has been set to {channel.mention}.", ephemeral=True
    )
    # Log the action of setting the welcome channel
    await log_action(f"Welcome channel has been set to {channel.mention} by {interaction.user}.", interaction.guild, interaction.channel)


# Error handler for set_welcome_channel command
@set_welcome_channel.error
async def set_welcome_channel_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            "You do not have the required permissions to set the welcome channel.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "An error occurred while setting the welcome channel.", ephemeral=True
        )

# Help command
@bot.tree.command(name="help", description="Show available commands.")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message("Available commands:/setwelcomechannel,/setverifyrole,setverifychannel, /starttimer, /sourcecode, /hello, /activity, /news, /image, /message, etc.")
    await log_action(f"{interaction.user} accessed the help menu.", interaction.guild, interaction.channel)

# Command to set verifying channel
@bot.tree.command(name="setverifychannel", description="Set the channel for verifying messages.")
@app_commands.checks.has_permissions(administrator=True)
async def set_verify_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    # Update the verifying channel in the database
    settings = get_guild_settings(interaction.guild.id)
    if settings:
        set_guild_settings(interaction.guild.id, settings[1], channel.id, settings[3])

    await interaction.response.send_message(
        f"Verifying channel has been set to {channel.mention}.", ephemeral=True
    )

    # Log the channel setting action
    await log_action(f"Channel set to {channel.mention} by {interaction.user}.", interaction.guild, interaction.channel)

# Command to set verifying role
@bot.tree.command(name="setverifyrole", description="Set the role for verifying.")
@app_commands.checks.has_permissions(administrator=True)
async def set_verify_role(interaction: discord.Interaction, role: discord.Role):
    # Update the verifying role in the database
    settings = get_guild_settings(interaction.guild.id)
    if settings:
        set_guild_settings(interaction.guild.id, settings[1], settings[2], role.id)

    await interaction.response.send_message(
        f"Verifying role has been set to {role.mention}.", ephemeral=True
    )

    # Log the role setting action
    await log_action(f"Role set to {role.mention} by {interaction.user}.", interaction.guild, interaction.channel)

@bot.tree.command(name="verify", description="Verify yourself.")
async def verify(interaction: discord.Interaction):
    settings = get_guild_settings(interaction.guild.id)
    print(f"Verify command settings: {settings}")
    if not settings or not settings[2]:
        await interaction.response.send_message("Verification channel is not set.", ephemeral=True)
        return

    verify_channel_id = settings[2]
    if interaction.channel.id != verify_channel_id:
        await interaction.response.send_message(f"This command can only be used in the verify channel.", ephemeral=True) 
        return

    # Verification logic...
    verify_role_id = settings[3]
    verify_role = interaction.guild.get_role(verify_role_id)
    if verify_role:
        await interaction.user.add_roles(verify_role)
        await interaction.response.send_message("You have been verified!", ephemeral=True)

        # Log action with the correct guild object
        await log_action(f"{interaction.user} has been verified and assigned the {verify_role.name} role.", interaction.guild, interaction.channel)
    else:
        await interaction.response.send_message("Verification role is not set.", ephemeral=True)

@bot.tree.command(name="message", description="Send a message to a selected channel")
async def message(interaction: discord.Interaction, channel: discord.TextChannel, message_content: str):
    message_content = message_content.replace(r"\n", "\n")
    # Send the user-provided message to the selected channel
    await channel.send(message_content)
    
    # Send a response to the user only (ephemeral)
    await interaction.response.send_message(f"Message sent to {channel.mention}!", ephemeral=True)
    
    # Log the action after sending the message
    await log_action(f"Message sent to {channel.mention} by {interaction.user}. Content: {message_content}", interaction.guild, interaction.channel)

# Command to send an image to a channel
@bot.tree.command(name="image", description="Send an image to a specified channel using a URL")
@app_commands.describe(
    channel="The channel to send the image to", 
    image_url="The URL of the image to send",
    caption="Optional caption for the image"
)
async def send_image(interaction: discord.Interaction, channel: discord.TextChannel, image_url: str, caption: str = ""):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    with open("temp_image.jpg", "wb") as f:
                        f.write(await response.read())
                    await channel.send(content=caption, file=discord.File("temp_image.jpg"))
                    os.remove("temp_image.jpg")
                    await interaction.response.send_message(f"Image sent to {channel.mention}!", ephemeral=True)
                else:
                    await interaction.response.send_message("Failed to fetch the image. Please check the URL.", ephemeral=True)
        await log_action(f"Image sent to {channel.mention} by {interaction.user} with caption: {caption}", interaction.guild, interaction.channel)
    except Exception as e:
        await interaction.response.send_message(f"Error sending image: {e}", ephemeral=True)

@bot.tree.command(name="starttimer", description="Starts a timer that will send a message when the target time (hr:min) is reached")
@app_commands.describe(hour="The hour (24-hour format) of the target time", minute="The minute of the target time", message="The message to send", image_url="Optional image URL or file path to include in the message")
async def start_timer(interaction: discord.Interaction, hour: int, minute: int, message: str, image_url: str = None):
    # Defer the response to avoid timeout
    await interaction.response.defer()

    # Get the current time
    now = datetime.now()

    # Set the target time for today
    target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If the target time has already passed today, set the target time for the next day
    if target_time < now:
        target_time += timedelta(days=1)

    # Calculate the time difference
    time_diff = target_time - now

    # Send an ephemeral message to inform the user that the timer has been set (only visible to the user)
    await interaction.followup.send(f"Timer set for {target_time.strftime('%H:%M')}!", ephemeral=True)

    # Log the timer setup action (this will be visible to you or admins if you want)
    await log_action(f"Timer set for {target_time.strftime('%H:%M')} by {interaction.user}. Message: {message}", interaction.guild, interaction.channel)

    # Wait until the target time is reached
    await asyncio.sleep(time_diff.total_seconds())
    
    # Ensure line breaks in the message are properly handled
    message = message.replace(r"\n", "\n")

    # Send the message to the channel (this will be visible to everyone)
    await interaction.channel.send(message)

    # If an image URL or file path is provided
    if image_url:
        if os.path.isfile(image_url):  # If it's a local file
            await interaction.channel.send(file=discord.File(image_url))
        else:  # If it's a URL
            await interaction.channel.send(image_url)  # Just send the URL as a separate message
    else:
        # Use followup.send() for an ephemeral message about no image
        await interaction.followup.send("No image provided.", ephemeral=True)

    # Log the action after the message and image are sent
    if image_url:
        await log_action(f"Timer triggered by {interaction.user}. Message sent: {message}. Image: {image_url}", interaction.guild, interaction.channel)
    else:
        await log_action(f"Timer triggered by {interaction.user}. Message sent: {message}. No image provided.", interaction.guild, interaction.channel)



bot.run(TOKEN)