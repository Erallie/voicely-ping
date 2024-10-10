import json
import discord
from discord import app_commands
from discord.ext import commands
from typing import List

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
intents.voice_states = True

# Set up the bot
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.default_settings = {
            "notify_count": 3,
            "reset_count": 0
        }
        self.notified_channels = {}
        # This dictionary will look like this: {
        #     "user_id": [channel_id_1, channel_id_2]
        # }
        # make sure to not notify people if they are already in the channel

    async def setup_hook(self):
        print(f"Setup complete for {self.user}")


# Create the bot instance with a command prefix
bot = Bot()

# Store users who want to be notified in a dictionary {guild_id: set(user_ids)}
# Load the data from the JSON file when the bot starts
pings = load_pings()

@bot.event
async def on_ready():
    """Triggered when the bot has successfully connected to Discord."""
    print(f'Logged in as {bot.user}')

class VoiceChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Select one or more channels", min_values=1, max_values=25)
        self.channel_types = [discord.ChannelType.voice]

    async def callback(self, interaction: discord.Interaction):
        if len(self.values) <= 0:
            await interaction.response.send_message(f"You must select at least one channel!", ephemeral=True)
            return
        
        
        links = []
        for channel in self.values:
            links.append(f"- https://discord.com/channels/{interaction.guild_id}/{channel.id}")

        all_links = "\n".join(links)

        if len(links) > 1:
            plural = "s"
            channel = "any of the following channels"
        else:
            plural = ""
            channel = "the following channel"

        confirmation_embed = discord.Embed(title="Selected channels", description=f"You have selected the following channel{plural}:")

        channel_list = discord.Embed(description=all_links)
        
        count_embed = discord.Embed(title="Set notify count", description=f"In the modal that opens, type a number that represents the **number of people** that need to be in the channel{plural} you selected for you to be notified.\n\nYou won\'t be notified again until after everyone has left the channel.")
        # await interaction.response.send_modal(AddPingCountModal(self.values, all_links))
        
        await interaction.response.send_message(embeds=[confirmation_embed, channel_list, count_embed], view=OpenModalView(self.values, all_links), ephemeral=True)

class AddPingChannelView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(VoiceChannelSelect())

class AddPingCountModal(discord.ui.Modal, title="Setup new ping(s)"):
    plural = ""
    channel_ref = ""
    
    def __init__(self, channels: List[discord.app_commands.AppCommandChannel], links: str):
        super().__init__()
        self.channels = channels
        self.links = links
        if len(channels) > 1:
            self.plural = "s"
            self.channel_ref = "any of the following channels"
        else:
            self.plural = ""
            self.channel_ref = "the following channel"
        # self.add_item(VoiceChannelSelect())
    

    notify_count = discord.ui.TextInput(
        label="Member count",
        placeholder=str(bot.default_settings["notify_count"]),
        max_length=3,
        style=discord.TextStyle.short
        
    )

    async def on_submit(self, interaction: discord.Interaction):
        # if not self.notify_count.value:
        #     notify_count = bot.default_settings["notify_count"]
        # else:
        try:
            notify_count = int(self.notify_count.value)
        except:
            await interaction.response.send_message(f"{self.notify_count.value} is not a valid number! Only positive whole numbers are allowed.", ephemeral=True)
            return
            
        notify_str = str(notify_count)
        
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        # Add the user to the notification set for the guild
        if guild_id not in pings:
            pings[guild_id] = {}
        # if user_id not in pings[guild_id]:
        #     pings[guild_id][user_id] = {}

        for channel in self.channels:
            channel_id = str(channel.id)
            if channel_id not in pings[guild_id]:
                pings[guild_id][channel_id] = {}
            if notify_str not in pings[guild_id][channel_id]:
                pings[guild_id][channel_id][notify_str] = []
            
            if user_id not in pings[guild_id][channel_id][notify_str]:
                pings[guild_id][channel_id][notify_str].append(user_id)

            # region example
            # This dictionary will look something like this:
            # {
            #     guild_id_1: {
            #         channel_id_1: {
            #             count_1: [user_id_1, user_id_2],
            #             count_2: [user_id_1, user_id_2]
            #         },
            #         channel_id_2: {
            #             count_1: [user_id_1, user_id_2],
            #             count_2: [user_id_1, user_id_2]
            #         }
            #     },
            #     guild_id_2: {
            #         channel_id_1: {
            #             count_1: [user_id_1, user_id_2],
            #             count_2: [user_id_1, user_id_2]
            #         },
            #         channel_id_2: {
            #             count_1: [user_id_1, user_id_2],
            #             count_2: [user_id_1, user_id_2]
            #         }
            #     }
            # }
            # endregion

        save_pings()

        if len(self.channels) > 1:
            plural = "s"
            channel = "any of the following channels"
        else:
            plural = ""
            channel = "the following channel"

        if notify_count > 1:
            people = "people"
            verb = "are"
        else:
            people = "person"
            verb = "is"

            
        confirmation_embed = discord.Embed(title=f"Ping{plural} set!", description=f'You will be notified when **{notify_count} {people}** {verb} in {channel}:')

        channel_list = discord.Embed(description=self.links)
        # Respond to the user with the text they entered.
        await interaction.response.send_message(embeds=[confirmation_embed, channel_list], ephemeral=True)

class OpenModalView(discord.ui.View):
    def __init__(self, channels: List[discord.app_commands.AppCommandChannel], links: str):
        super().__init__()
        self.channels = channels
        self.links = links
    @discord.ui.button(label="Continue")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddPingCountModal(self.channels, self.links))

@bot.hybrid_group()
async def ping(ctx: commands.Context):
    """Add or remove a ping."""
    if ctx.invoked_subcommand is None:
        await ctx.send(f"{ctx.invoked_subcommand} is not a valid subcommand.", reference=ctx.message, ephemeral=True)

@ping.command()
async def add(ctx: commands.Context):
    """Add a voice channel for you to be notified for."""

    embed = discord.Embed(title="Setup new ping(s)", description='Choose from the dropdown to specify **one or more channels** to be notified for.')
    await ctx.send(embed=embed, view=AddPingChannelView(), reference=ctx.message, ephemeral=True)

@ping.command()
async def remove(ctx: commands.Context):
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
    # region Reset pings
    if before.channel is not None and len(before.channel.members) == 0:
        for user in bot.notified_channels:
            if before.channel.id in bot.notified_channels[user]:
                bot.notified_channels[user].remove(before.channel.id)
    # endregion
    # region Ping
    if after.channel is not None:
        member_list = after.channel.members
        count = len(member_list)
        count_str = str(count)
        guild_id = str(after.channel.guild.id)
        channel_id = str(after.channel.id)
        if guild_id in pings and channel_id in pings[guild_id] and count_str in pings[guild_id][channel_id]:
            for pinged_user_id in pings[guild_id][channel_id][count_str]:
                pinged_user = await bot.fetch_user(pinged_user_id)

                if count <= 5:
                    members_message = ""
                    for x in range(count):
                        if x == 0 and (count == 2 or count == 1):
                            members_message += f"<@{member_list[x].id}>"
                        elif x < count - 1:
                            members_message += f"<@{member_list[x].id}>, "
                        else:
                            members_message += f"and <@{member_list[x].id}>"
                else:
                    members_message = f"**{count_str}** members"

                if count == 1:
                    verb = "is"
                else:
                    verb = "are"
                
                try:
                    await pinged_user.send(f"{members_message} {verb} currently in https://discord.com/channels/{guild_id}/{channel_id}")
                except discord.Forbidden as error:
                    print(f"Could not send ping to {pinged_user.name}: {error}")
    # endregion


@bot.command()
@commands.is_owner()
@app_commands.describe(guild="The server ID of the server you want to sync commands to.")
async def sync(ctx: commands.Context, guild: discord.Guild = None):
    """Sync slash commands either globally or for a specific guild."""

    # print("sync triggered")

    if guild:
        synced_commands = await bot.tree.sync(guild=guild)
        command_list = ""
        for command in synced_commands:
            command_list += f"\n- `/{command.name}`"
        await ctx.send(f"Commands synced to the guild: {guild.name}{command_list}\nPlease note it may take up to an hour to propagate globally.", reference=ctx.message, ephemeral=True)
    else:
        try:
            synced_commands = await bot.tree.sync()
        except discord.app_commands.CommandSyncFailure as error:
            print(f"CommandSyncFailure: {error}")
        except discord.HTTPException as error:
            print(f"HTTPException: {error}")
        except discord.Forbidden as error:
            print(f"Forbidden: {error}")
        except discord.app_commands.TranslationError as error:
            print(f"TranslationError: {error}")
        # print("synced commands globally")
        command_list = ""
        for command in synced_commands:
            command_list += f"\n- `/{command.name}`"
        await ctx.send(f"Commands synced globally:{command_list}\nPlease note it may take up to an hour to propagate globally.", reference=ctx.message, ephemeral=True)


# Run the bot with the loaded token
bot.run(bot_token)
