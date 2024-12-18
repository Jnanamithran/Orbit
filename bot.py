import discord
from discord.ext import commands

# Create the bot instance
intents = discord.Intents.default()
intents.members = True  # Allow the bot to manage members
bot = commands.Bot(command_prefix="!", intents=intents)

# Define the custom role ID and verification channel ID
CUSTOM_ROLE_ID = 1258114905291096075  # This should be the role ID, not name
VERIFY_CHANNEL_ID = 1319002480071278593  # Replace with your channel ID for verification announcement

@bot.tree.command(name="verify", description="Verify to get the custom role")
async def verify(interaction: discord.Interaction):
    member = interaction.user
    guild = interaction.guild

    # Check if the role exists by ID
    role = discord.utils.get(guild.roles, id=CUSTOM_ROLE_ID)
    
    if not role:
        await interaction.response.send_message(f"Role with ID {CUSTOM_ROLE_ID} not found.", ephemeral=True)
        print(f"Role with ID {CUSTOM_ROLE_ID} not found.")
        return

    # Check if the bot can assign the role
    if interaction.user.top_role <= role:
        await interaction.response.send_message("I don't have permission to assign this role.", ephemeral=True)
        print("Bot doesn't have permission to assign the role.")
        return

    # Assign the role to the member
    await member.add_roles(role)
    
    # Send a confirmation message in the verification channel
    verify_channel = guild.get_channel(VERIFY_CHANNEL_ID)
    if verify_channel:
        await verify_channel.send(f"{member.mention} has been verified! Welcome to the server!")
    else:
        await interaction.response.send_message("Could not find the verification channel.", ephemeral=True)

    # Acknowledge the verification
    await interaction.response.send_message(f"You have been verified and assigned the {role.name} role!", ephemeral=True)

    # Optionally, send a reminder message in the server
    await verify_channel.send("New members, please type `/verify` to get verified and access the server!")

# Replace with your bot token
bot.run("YOUR BOT TOKEN")
