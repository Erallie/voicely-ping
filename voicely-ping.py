import json
import discord
from discord.ext import commands

# Load bot token from file
with open('../token', 'r') as file:
    bot_token = file.read().strip()

# Load notify data from file (or return an empty dictionary if the file doesn't exist)
def load_pings():
    try:
        with open('pings.json', 'r') as f:
            # Load JSON data into a dictionary
            return json.load(f)
    except FileNotFoundError as error:
        print(f"Cannot load pings.json: {error}")
        # If the file doesn't exist, return an empty dictionary
        return {}

# Save the current notify data to a JSON file
def save_pings():
    with open('pings.json', 'w') as f:
        # Write the dictionary to the JSON file
        json.dump(pings, f)

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.messages = True
intents.members = True

# Create the bot instance with a command prefix
bot = commands.Bot(command_prefix='!', intents=intents)

# Store users who want to be notified in a dictionary {guild_id: set(user_ids)}
# Load the data from the JSON file when the bot starts
pings = load_pings()

@bot.event
async def on_ready():
    """Triggered when the bot has successfully connected to Discord."""
    print(f'Logged in as {bot.user}')

@bot.hybrid_command()
async def addping(ctx: commands.Context):
    """
    Command for users to enable notifications.
    Adds the user ID to the set of users to be notified for the current guild.
    """
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    # Add the user to the notification set for the guild
    if guild_id not in pings:
        pings[guild_id] = set()
    pings[guild_id].add(user_id)
    # Save the updated notification list to the JSON file
    save_pings()
    await ctx.send(f'{ctx.author.mention}, you will be notified when someone joins a voice channel.')

@bot.hybrid_command()
async def removeping(ctx: commands.Context):
    """
    Command for users to disable notifications.
    Removes the user ID from the set of users to be notified for the current guild.
    """
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    # Remove the user from the notification set for the guild, if they exist
    if guild_id in pings and user_id in pings[guild_id]:
        pings[guild_id].remove(user_id)
        # Save the updated notification list to the JSON file
        save_pings()
        await ctx.send(f'You will no longer receive voice channel notifications.', reference=ctx.message, ephemeral=True)
    else:
        await ctx.send(f'You were not signed up for notifications.', reference=ctx.message, ephemeral=True)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """
    Event triggered when a user's voice state changes.
    Checks if a user has joined a voice channel and sends a DM to users who opted in for notifications.
    """
    # Check if the user joined a voice channel (wasn't in one before, but now is)
    if before.channel is None and after.channel is not None:
        guild_id = str(member.guild.id)
        # Get users to notify for this guild
        if guild_id in pings:
            channel_link = f"https://discord.com/channels/{guild_id}/{after.channel.id}"
            # Notify all users who opted in
            for user_id in pings[guild_id]:
                user = bot.get_user(int(user_id))
                if user:
                    try:
                        # Send a DM with the link to join the voice channel
                        await user.send(
                            f'{member.name} has joined {after.channel.name}. Click here to join: {channel_link}'
                        )
                    except discord.Forbidden:
                        # Handle cases where the bot can't DM the user (e.g., DMs are disabled)
                        print(f'Could not send DM to {user.name}')

# Run the bot with the loaded token
bot.run(bot_token)
