import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import asyncio
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

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

# Function to log actions to a specific server and channel
async def log_action(message: str, guild, channel):
    # Get the target guild where logs will be sent
    target_guild = bot.get_guild(TARGET_GUILD_ID)
    
    if target_guild:
        # Get the log channel in the target guild
        log_channel = target_guild.get_channel(LOG_CHANNEL_ID)
        
        if log_channel:
            # Get the current time in IST
            ist_time = datetime.now(IST)
            timestamp = ist_time.strftime('%Y-%m-%d %H:%M:%S')

            log_message = (
                f"**[{timestamp}]**\n"
                f"**Server**: {guild.name}\n"
                f"**Channel**: #{channel.name}\n"
                f"**Action**: {message}\n"
            )
            try:
                # Send the log message to the log channel in the target guild
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
    try:
        await bot.tree.sync()
        print(f"Logged in as {bot.user} and synced commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

    # Set bot's initial status
    await bot.change_presence(
        activity=discord.Game(name="Watching You"),
        status=discord.Status.dnd,
    )
    print(f"Bot is now online as {bot.user}.")
    
    # Log bot startup action to the log channel of the target guild
    target_guild = bot.get_guild(TARGET_GUILD_ID)
    if target_guild:
        log_channel = target_guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            timestamp = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
            log_message = f"[{timestamp}] Bot started and connected to the server: {target_guild.name}."
            await log_channel.send(log_message)
        else:
            print("Log channel not found!")

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

            # Log the action of sending the welcome message
            await log_action(f"Sent welcome message to {member.mention} in {welcome_channel.mention}.", member.guild, welcome_channel)

# Command to set welcome channel
@bot.tree.command(name="setwelcomechannel", description="Set the channel for welcome messages.")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    # Store the channel ID for the server (in memory)
    welcome_channels[str(interaction.guild.id)] = channel.id

    # Log the action of setting the welcome channel
    await log_action(f"Welcome channel has been set to {channel.mention} by {interaction.user}.", interaction.guild, interaction.channel)

    await interaction.response.send_message(
        f"Welcome channel has been set to {channel.mention}.", ephemeral=True
    )

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
    await interaction.response.send_message("Available commands: /starttimer, /sourcecode, /hello, /activity, /news, /image, /message, etc.")
    await log_action(f"{interaction.user} accessed the help menu.", interaction.guild, interaction.channel)

# Command to get the bot's source code
@bot.tree.command(name="sourcecode", description="Get the bot's source code")
async def source_code(interaction: discord.Interaction):
    try:
        file_path = os.path.abspath("E:\\Program\\DiscordBot\\Orbit\\bot.py")  # Update with your file path

        if os.path.isfile(file_path):
            await interaction.response.send_message(
                content="Here is the bot's source code:",
                file=discord.File(file_path),
                ephemeral=True
            )
            await log_action(f"Source code requested by {interaction.user}.", interaction.guild, interaction.channel)
        else:
            await interaction.response.send_message(
                "The source code file could not be found.",
                ephemeral=True
            )
    except Exception as e:
        await interaction.response.send_message(
            f"Failed to fetch the source code: {e}",
            ephemeral=True
        )

# Command to set a channel for the bot to use
@bot.tree.command(name="setchannel", description="Set a channel for the bot to use")
@app_commands.describe(channel="The channel to set")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild_id
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {}
    guild_settings[guild_id]['channel_id'] = channel.id
    await interaction.response.send_message(f"Channel set to {channel.mention}", ephemeral=True)

    # Log the channel setting action
    await log_action(f"Channel set to {channel.mention} by {interaction.user}.", interaction.guild, interaction.channel)

# Command to set a role for the bot to use
@bot.tree.command(name="setrole", description="Set a role for the bot to use")
@app_commands.describe(role="The role to set")
async def set_role(interaction: discord.Interaction, role: discord.Role):
    guild_id = interaction.guild_id
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {}
    guild_settings[guild_id]['role_id'] = role.id
    await interaction.response.send_message(f"Role set to {role.mention}", ephemeral=True)

    # Log the role setting action
    await log_action(f"Role set to {role.mention} by {interaction.user}.", interaction.guild, interaction.channel)

# Command to view current settings
@bot.tree.command(name="viewsettings", description="View the current channel and role settings")
async def view_settings(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    settings = guild_settings.get(guild_id, {})
    channel_id = settings.get('channel_id', 'Not set')
    role_id = settings.get('role_id', 'Not set')
    await interaction.response.send_message(
        f"Current settings:\nChannel: <#{channel_id}>\nRole: <@&{role_id}>",
        ephemeral=True
    )

    # Log the view settings action
    await log_action(f"Settings viewed by {interaction.user}.", interaction.guild, interaction.channel)

# Command to verify and give a custom role
@bot.tree.command(name="verify", description="Verify to get the custom role")
async def verify(interaction: discord.Interaction):
    guild = interaction.guild
    member = interaction.user

    guild_id = guild.id
    settings = guild_settings.get(guild_id, {})
    role_id = settings.get('role_id')

    if not role_id:
        await interaction.response.send_message("The verification role has not been set. Please contact an admin.", ephemeral=True)
        return

    role = discord.utils.get(guild.roles, id=role_id)
    if not role:
        await interaction.response.send_message("Role not found. Please contact an admin.", ephemeral=True)
        return

    try:
        await member.add_roles(role)
        await interaction.response.send_message(f"You've been verified and given the {role.name} role!", ephemeral=True)
        await log_action(f"{interaction.user} has been verified and assigned the {role.name} role.", guild, interaction.channel)
    except Exception as e:
        await interaction.response.send_message("An error occurred while assigning the role. Please contact an admin.", ephemeral=True)

# Command to send a custom message to a channel
@bot.tree.command(name="message", description="Send a custom message to a specified channel")
@app_commands.describe(channel="The channel to send the message to", message="The message to send")
async def send_message(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    try:
        await channel.send(content=message)
        await interaction.response.send_message(f"Message sent to {channel.mention}!", ephemeral=True)

        # Log the message sent action
        await log_action(f"Message sent to {channel.mention} by {interaction.user}: {message}", interaction.guild, interaction.channel)
    except Exception as e:
        await interaction.response.send_message(f"Error sending message: {e}", ephemeral=True)

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

# Command to start a timer
@bot.tree.command(name="starttimer", description="Start a timer for a specified duration")
@app_commands.describe(duration="Duration in minutes for the timer")
async def start_timer(interaction: discord.Interaction, duration: int):
    await interaction.response.send_message(f"Timer started for {duration} minutes.", ephemeral=True)

    await log_action(f"Timer started for {duration} minutes by {interaction.user}.", interaction.guild, interaction.channel)

    await asyncio.sleep(duration * 60)  # Convert minutes to seconds
    await interaction.followup.send(f"{interaction.user.mention}, the timer for {duration} minutes has ended.")

bot.run(TOKEN)
