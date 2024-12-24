import discord
from discord.ext import commands
from discord import app_commands

# Create the bot instance
intents = discord.Intents.default()
intents.members = True  # Allow the bot to manage members
bot = commands.Bot(command_prefix="!", intents=intents)

# A dictionary to store channel and role IDs for each guild
guild_settings = {}

# Event to sync slash commands
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print(f"Logged in as {bot.user} and synced commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Slash command to set a channel
@bot.tree.command(name="setchannel", description="Set a channel for the bot to use")
@app_commands.describe(channel="The channel to set")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild_id
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {}
    guild_settings[guild_id]['channel_id'] = channel.id
    await interaction.response.send_message(f"Channel set to {channel.mention}", ephemeral=True)

# Slash command to set a role
@bot.tree.command(name="setrole", description="Set a role for the bot to use")
@app_commands.describe(role="The role to set")
async def set_role(interaction: discord.Interaction, role: discord.Role):
    guild_id = interaction.guild_id
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {}
    guild_settings[guild_id]['role_id'] = role.id
    await interaction.response.send_message(f"Role set to {role.mention}", ephemeral=True)

# Slash command to view current settings
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

# Slash command for verification
@bot.tree.command(name="verify", description="Verify to get the custom role")
async def verify(interaction: discord.Interaction):
    print("Verify command triggered.")

    guild = interaction.guild
    if not guild:
        print("Guild is None (likely used in DMs).")
        await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
        return

    member = interaction.user
    print(f"User: {member.display_name}")

    guild_id = guild.id
    settings = guild_settings.get(guild_id, {})
    role_id = settings.get('role_id')

    if not role_id:
        print("Role not set in settings.")
        await interaction.response.send_message("The verification role has not been set. Please contact an admin.", ephemeral=True)
        return

    # Check if the role exists
    role = discord.utils.get(guild.roles, id=role_id)
    if not role:
        print(f"Role with ID {role_id} not found.")
        await interaction.response.send_message("Role not found. Please contact an admin.", ephemeral=True)
        return

    # Check if the bot can assign the role
    if guild.me.top_role <= role:
        print("Bot doesn't have permission to assign the role.")
        await interaction.response.send_message("I can't assign this role. Please contact an admin.", ephemeral=True)
        return

    # Assign the role to the member
    try:
        await member.add_roles(role)
        print(f"Assigned role {role.name} to {member.display_name}.")
        await interaction.response.send_message(f"You've been verified and given the {role.name} role!", ephemeral=True)
    except Exception as e:
        print(f"Error assigning role: {e}")
        await interaction.response.send_message("An error occurred while assigning the role. Please contact an admin.", ephemeral=True)
        return

# Slash command to set a welcome channel
@bot.tree.command(name="setwelcomechannel", description="Set a channel for the welcome messages")
@app_commands.describe(channel="The channel to set as the welcome channel")
async def set_welcome_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild_id
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {}
    guild_settings[guild_id]['welcome_channel_id'] = channel.id
    await interaction.response.send_message(f"Welcome channel set to {channel.mention}", ephemeral=True)

# Event triggered when a new member joins the server
@bot.event
async def on_member_join(member: discord.Member):
    guild_id = member.guild.id
    settings = guild_settings.get(guild_id, {})
    welcome_channel_id = settings.get('welcome_channel_id')

    if not welcome_channel_id:
        print("Welcome channel not set.")
        return

    welcome_channel = member.guild.get_channel(welcome_channel_id)
    if welcome_channel:
        # Create an aesthetic welcome message
        welcome_message = f"🌟 **Welcome to {member.guild.name}, {member.mention}!** 🌟\nWe're glad to have you here! 🎉\nEnjoy your stay and explore the server!"
        await welcome_channel.send(welcome_message)
    else:
        print("Welcome channel not found.")

@bot.tree.command(name="message", description="Send a custom message to a specified channel")
@app_commands.describe(channel="The channel to send the message to", message="The message to send")
async def send_message(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    try:
        # Send the message to the specified channel
        await channel.send(message)
        await interaction.response.send_message(f"Message sent to {channel.mention}!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Error sending message: {e}", ephemeral=True)


@bot.event
async def on_ready():
    await bot.tree.sync()
    await bot.change_presence(status=discord.Status.dnd,activity=discord.Game(name="Watching You"))
    # Specify the channel ID where you want to send the message
    channel = bot.get_channel(1319320727861727272)  # Replace YOUR_CHANNEL_ID with the actual channel ID
    if channel:
        await channel.send("Bot is now online!")  # Send a message to the specified channel
    print(f'Logged in as {bot.user}')   

# Replace with your bot token
bot.run("YOUR BOT TOKEN")
