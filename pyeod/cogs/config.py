from discord.ext import commands, tasks, bridge, pages
from discord.utils import get
from discord import User, Message, TextChannel
from pyeod.model import InternalError
from pyeod.frontend import DiscordGameInstance, InstanceManager
from pyeod.utils import format_traceback
from pyeod import config
import traceback
import os


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.manager = None

    @commands.Cog.listener()
    async def on_ready(self):
        print("Loading instance manager")
        self.manager = InstanceManager()
        # TODO: load manager here?

    @commands.Cog.listener("on_message")
    async def check_for_new_servers(self, msg: Message):
        if not self.manager:  # Messages can be caught before bot is ready
            return
        if msg.guild and msg.guild not in self.manager:
            self.manager.add_instance(msg.guild.id, DiscordGameInstance())

    # Slash commands only cus converting to channel is busted
    @commands.slash_command()
    async def add_play_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        # TODO: Add permissions locks so that only certain roles can add channels

        if ctx.guild and ctx.guild.id not in self.manager:
            self.manager.add_instance(ctx.guild.id, DiscordGameInstance())

        # If converting is fixed
        # if isinstance(
        #    ctx, bridge.BridgeExtContext
        # ):  # If it's a text command convert the channel arg to an actual channel object
        #    if "<#" in channel:
        #        channel = self.bot.get_channel(
        #            int(channel.replace("<#", "").replace(">", ""))
        #        )
        #    else:
        #        channel = get(ctx.guild.channels, name=channel)

        server = self.manager.get_instance(ctx.guild.id)

        server.channels.play_channels.append(channel)

        await ctx.respond(f"Successfully added {channel.name} as a play channel!")

    @bridge.bridge_command()
    async def user(self, ctx: bridge.BridgeContext, user: User):
        await ctx.respond(f"User: {user.id}")


def setup(client):
    client.add_cog(Config(client))
