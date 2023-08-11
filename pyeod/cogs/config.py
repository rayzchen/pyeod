from discord.ext import commands, tasks, bridge, pages
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
        print("Loading instance manager")
        # Manager instance is stored under InstanceManager.current
        manager = InstanceManager()
        # TODO: load manager here?

    @commands.Cog.listener("on_message")
    async def check_for_new_servers(self, msg: Message):
        if InstanceManager.current:  # Messages can be caught before bot is ready
            return
        InstanceManager.current.get_or_create(msg.guild.id, DiscordGameInstance)

    # Slash commands only cus converting to channel is busted
    @commands.slash_command()
    async def add_play_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        # TODO: Add permissions locks so that only certain roles can add channels

        server = InstanceManager.current.get_or_create(ctx.guild.id, DiscordGameInstance)
        server.channels.play_channels.append(channel.id)
        await ctx.respond(f"Successfully added {channel.name} as a play channel!")

    @commands.slash_command()
    async def remove_play_channel(
        self, ctx: bridge.BridgeContext, channel: TextChannel
    ):
        # TODO: Add permissions locks so that only certain roles can add channels

        server = InstanceManager.current.get_or_create(ctx.guild.id, DiscordGameInstance)

        try:
            server.channels.play_channels.remove(channel.id)
            await ctx.respond(f"Successfully removed {channel.name} as a play channel!")
        except ValueError:
            await ctx.respond(f"That is not a play channel")

    @commands.slash_command()
    async def set_news_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        # TODO: Add permissions locks so that only certain roles can add channels

        server = InstanceManager.current.get_or_create(ctx.guild.id, DiscordGameInstance)
        server.channels.news_channel = channel.id
        await ctx.respond(f"Successfully set {channel.name} as the news channel!")

    @commands.slash_command()
    async def set_voting_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        # TODO: Add permissions locks so that only certain roles can add channels

        server = InstanceManager.current.get_or_create(ctx.guild.id, DiscordGameInstance)
        server.channels.voting_channel = channel.id
        await ctx.respond(f"Successfully set {channel.name} as the voting channel!")


def setup(client):
    client.add_cog(Config(client))
