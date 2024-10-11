import json
import discord
from discord import app_commands
from discord.ext import commands
from typing import List
import math

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
intents.members = True

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

# region views and modals

# region add ping
class VoiceChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Select one or more channels", min_values=1, max_values=25)
        self.channel_types = [discord.ChannelType.voice]

    async def callback(self, interaction: discord.Interaction):
        if len(self.values) <= 0:
            await interaction.response.send_message(f"You must select at least one channel!", ephemeral=True)
            return
        
        # links = []
        all_links = ""
        for channel in self.values:
            # links.append(f"- https://discord.com/channels/{interaction.guild_id}/{channel.id}")
            all_links += f"\n- https://discord.com/channels/{interaction.guild_id}/{channel.id}"

        # all_links = "\n".join(links)

        if len(self.values) > 1:
            plural = "s"
            channel = "any of the following channels"
        else:
            plural = ""
            channel = "the following channel"

        confirmation_embed = discord.Embed(title="Selected channels", description=f"You have selected the following channel{plural}:{all_links}")

        # channel_list = discord.Embed(description=all_links)
        
        count_embed = discord.Embed(title="Set notify count", description=f"In the modal that opens, type a number that represents the **number of people** that need to be in the channel{plural} you selected for you to be notified.\n\nYou won\'t be notified again until after everyone has left the channel.")
        
        await interaction.response.send_message(embeds=[confirmation_embed, count_embed], view=OpenModalView(self.values, all_links), ephemeral=True)

class AddPingChannelView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(VoiceChannelSelect())

class AddPingCountModal(discord.ui.Modal, title="Specify member count"):
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

        error_message = f"`{self.notify_count.value}` is not a valid number! Only positive whole numbers are allowed."

        try:
            notify_count = int(self.notify_count.value)
        except:
            await interaction.response.send_message(error_message, ephemeral=True)
        
        else:
            if notify_count <= 0:
                await interaction.response.send_message(error_message, ephemeral=True)
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
# endregion

# region remove ping
class RemovePingSelect(discord.ui.Select):    
    def setup_select(self, options_dict: List[dict]):
        options: List[discord.SelectOption] = []
        for dict in options_dict:
            # channel_str = dict["channel_str"]
            count_str = dict["count_str"]
            try:
                count = int(count_str)
            except:
                print(f"Error converting {count_str} to an int.")
                count = None
            
            if count is None:
                plural = "(s)"
            elif count > 1:
                plural = "s"
            else:
                plural = ""
            options.append(discord.SelectOption(label=f"{dict["channel_name"]}: {count_str} member{plural}", value=f"{dict['guild_str']}/{dict["channel_str"]}/{count_str}", description=dict["guild_name"]))
        return options
        
    def set_placeholder(self, options: List[dict]):
        start_guild: str = options[0]["guild_name"]
        end_guild: str = options[len(options) - 1]["guild_name"]

        if start_guild == end_guild:
            return f"Pings in {start_guild}"
        else:
            return f"Servers {start_guild} to {end_guild}"
    

    def __init__(self, options: List[discord.SelectOption], index: int):
        super().__init__(min_values=1, max_values=len(options), options = self.setup_select(options), placeholder=self.set_placeholder(options))


    async def callback(self, interaction: discord.Interaction):
        if len(self.values) <= 0:
            await interaction.response.send_message(f"You must select at least one ping!", ephemeral=True)
            return
        
        for value in self.values:
            values = value.split('/')
            guild_id = values[0]
            channel_id = values[1]
            count_str = values[2]

            pings[guild_id][channel_id][count_str].remove(str(interaction.user.id))

            if len(pings[guild_id][channel_id][count_str]) == 0:
                del pings[guild_id][channel_id][count_str]
            if len(pings[guild_id][channel_id]) == 0:
                del pings[guild_id][channel_id]
            if len(pings[guild_id]) == 0:
                del pings[guild_id]

        save_pings()

        ping_count = len(self.values)
        if ping_count > 1:
            plural = "s"
        else:
            plural = ""
        await interaction.response.send_message(f"Successfully removed **{len(self.values)} ping{plural}**.", ephemeral=True)

class RemovePingView(discord.ui.View):
    pages = 0
    select_count = 0
    all_options: List[dict] = []
    count = 0
    def __init__(self, options: List[dict], page: int):
        super().__init__()
        self.all_options = options
        self.select_count = math.ceil(len(options) / 25)
        self.page = page
        if self.select_count == 5:
            self.pages = 1
        else:
            self.pages = math.ceil(self.select_count / 4)

        self.index = page * 4 * 25
        
        def add_option():
            options = self.all_options[self.index:min(self.index + 25, len(self.all_options))]
            select = RemovePingSelect(options, self.index)
            self.add_item(select)
            self.index += 25
            self.count += 1

        
        while (self.index < len(self.all_options)) and (self.count < 5):
            add_option()
        
        if self.pages == 1 and self.index < len(self.all_options):
            add_option()
        
# endregion

# endregion

# region Reused errors
def get_error(action: str, error = None):
    if error:
        return f"I could not {action}: {error}"
    return f"I encountered an error while trying to {action}."
# endregion

# region commands
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
    """Remove a ping that you previously set up."""
    # guild_id = str(ctx.guild.id)
    user_id_str = str(ctx.author.id)
    # Remove the user from the notification set for the guild, if they exist
    # listed_pings = {}
    options: List[dict] = []
    for guild_id_str in pings:
        for channel_id_str in pings[guild_id_str]:
            for count_str in pings[guild_id_str][channel_id_str]:
                if user_id_str in pings[guild_id_str][channel_id_str][count_str]:
                    
                    channel = bot.get_channel(int(channel_id_str))
                    guild = bot.get_guild(int(guild_id_str))

                    options.append({
                        "guild_str": guild_id_str,
                        "guild_name": guild.name,
                        "channel_str": channel_id_str,
                        "channel_name": channel.name,
                        "count_str": count_str
                    })
    
    if len(options) == 0:
        await ctx.send(f'You have not set up any pings to remove.', reference=ctx.message, ephemeral=True)
    else:
        def sort_options(option):
            guild_name: str = option["guild_name"]
            channel_name: str = option["channel_name"]

            count_str = option["count_str"]

            while len(count_str) < 3:
                count_str = f"0{count_str}"

            return f"{guild_name} {channel_name} {count_str}"

        options.sort(key=sort_options)
        embed = discord.Embed(title="Remove pings", description=f"Choose from the dropdowns below to remove those pings.")
        # view = RemovePingView(options, 0)
        await ctx.send(embed=embed, view=RemovePingView(options, 0), reference=ctx.message, ephemeral=True)


# endregion

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """
    Event triggered when a user's voice state changes.
    Checks if a user has joined a voice channel and sends a DM to users who opted in for notifications.
    """
    # region Reset pings
    if before.channel is not None and len(before.channel.members) == 0:
        for user_id in bot.notified_channels:
            if before.channel.id in bot.notified_channels[user_id]:
                bot.notified_channels[user_id].remove(before.channel.id)
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
                if pinged_user_id in bot.notified_channels:
                    if after.channel.id in bot.notified_channels[pinged_user_id]:
                        return
                else:
                    bot.notified_channels[pinged_user_id] = []
                    
                bot.notified_channels[pinged_user_id].append(after.channel.id)

                pinged_user = bot.get_user(int(pinged_user_id))

                for member in member_list:
                    if member.id == pinged_user.id:
                        return

                if count <= 5:
                    members_message = ""
                    for x in range(count):
                        if count == 1:
                            members_message += f"<@{member_list[x].id}>"
                        elif x == 0 and count == 2:
                            members_message += f"<@{member_list[x].id}> "
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
