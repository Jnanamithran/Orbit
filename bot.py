import discord
from discord.ext import commands
from discord import app_commands
import json  # For saving and loading emoji-role mappings

# Intents for monitoring reactions and member updates
intents = discord.Intents.default()
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load emoji-to-role mapping from a file
try:
    with open("emoji_to_role.json", "r") as file:
        emoji_to_role = json.load(file)
except FileNotFoundError:
    emoji_to_role = {}

# Global variables for channel and message ID
designated_channel_id = None
reaction_message_id = None

def save_emoji_to_role():
    """Save the emoji-to-role mapping to a file."""
    with open("emoji_to_role.json", "w") as file:
        json.dump(emoji_to_role, file)

@bot.event
async def on_ready():
    print(f"Bot is ready! Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.guild_id is None or not (designated_channel_id == payload.channel_id and reaction_message_id == payload.message_id):
        return

    guild = bot.get_guild(payload.guild_id)
    emoji_key = str(payload.emoji)
    role_id = emoji_to_role.get(emoji_key)

    if role_id:
        role = guild.get_role(role_id)
        member = guild.get_member(payload.user_id)
        if role and member:
            await member.add_roles(role)
            print(f"Assigned {role.name} to {member.name}")

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.guild_id is None or not (designated_channel_id == payload.channel_id and reaction_message_id == payload.message_id):
        return

    guild = bot.get_guild(payload.guild_id)
    emoji_key = str(payload.emoji)
    role_id = emoji_to_role.get(emoji_key)

    if role_id:
        role = guild.get_role(role_id)
        member = guild.get_member(payload.user_id)
        if role and member:
            await member.remove_roles(role)
            print(f"Removed {role.name} from {member.name}")

@bot.tree.command(name="setrole", description="Map an emoji to a role")
async def setrole(interaction: discord.Interaction, emoji: str, role: discord.Role):
    emoji_to_role[emoji] = role.id
    save_emoji_to_role()
    await interaction.response.send_message(f"Mapped emoji {emoji} to role {role.name}", ephemeral=True)

@bot.tree.command(name="setchannel", description="Set the designated channel for reactions")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    global designated_channel_id
    designated_channel_id = channel.id
    await interaction.response.send_message(f"Designated channel set to {channel.name}", ephemeral=True)

@bot.tree.command(name="message", description="Send a message as the bot")
async def message(interaction: discord.Interaction, content: str, channel: discord.TextChannel = None):
    def handle_newlines(text):
        return text.replace("\\n", "\n")

    processed_content = handle_newlines(content)
    target_channel = channel if channel else interaction.channel
    bot_message = await target_channel.send(processed_content)
    global reaction_message_id, designated_channel_id
    reaction_message_id = bot_message.id
    designated_channel_id = target_channel.id
    await interaction.response.send_message(f"Message sent in {target_channel.mention} and ready for reactions!", ephemeral=True)

@bot.tree.command(name="setreaction", description="Set a reaction emoji on the bot's message")
async def setreaction(interaction: discord.Interaction, emoji: str):
    if reaction_message_id:
        target_channel = interaction.guild.get_channel(designated_channel_id)
        if target_channel:
            bot_message = await target_channel.fetch_message(reaction_message_id)
            await bot_message.add_reaction(emoji)
            await interaction.response.send_message(f"Added reaction {emoji} to the message.", ephemeral=True)
        else:
            await interaction.response.send_message("Designated channel not found.", ephemeral=True)
    else:
        await interaction.response.send_message("No message found to react to. Use /message to send a new one.", ephemeral=True)

# Replace with your bot token
bot.run("MTMxNTI2NzAyNDI2Nzc3NjAwMA.GcXFpm.z73k5zz4Whu-3kU_6soJzSEfehaR9mNnzqPaM4")
