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
        self.bot.manager = None  # Move to dif module???

    @commands.Cog.listener()
    async def on_ready(self):
        print("Loading instance manager")
        self.bot.manager = InstanceManager()
        # TODO: load manager here?

    @commands.Cog.listener("on_message")
    async def check_for_new_servers(self, msg: Message):
        if not self.bot.manager:  # Messages can be caught before bot is ready
            return
        if msg.guild and msg.guild not in self.bot.manager:
            try:
                self.bot.manager.add_instance(msg.guild.id, DiscordGameInstance())
            except InternalError as i:
                if i.type == "Instance overwrite":  # Keeps happening don't know why
                    pass

    # Slash commands only cus converting to channel is busted
    @commands.slash_command()
    async def add_play_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        # TODO: Add permissions locks so that only certain roles can add channels

        if ctx.guild and ctx.guild.id not in self.bot.manager:
            self.bot.manager.add_instance(ctx.guild.id, DiscordGameInstance())

        server = self.bot.manager.get_instance(ctx.guild.id)

        server.channels.play_channels.append(channel)

        await ctx.respond(f"Successfully added {channel.name} as a play channel!")

    @commands.slash_command()
    async def remove_play_channel(
        self, ctx: bridge.BridgeContext, channel: TextChannel
    ):
        # TODO: Add permissions locks so that only certain roles can add channels

        if ctx.guild and ctx.guild.id not in self.bot.manager:
            self.bot.manager.add_instance(ctx.guild.id, DiscordGameInstance())

        server = self.bot.manager.get_instance(ctx.guild.id)

        try:
            server.channels.play_channels.remove(channel)
            await ctx.respond(f"Successfully removed {channel.name} as a play channel!")
        except ValueError:
            await ctx.respond(f"That is not a play channel")

    @commands.slash_command()
    async def add_news_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        # TODO: Add permissions locks so that only certain roles can add channels

        if ctx.guild and ctx.guild.id not in self.bot.manager:
            self.bot.manager.add_instance(ctx.guild.id, DiscordGameInstance())

        server = self.bot.manager.get_instance(ctx.guild.id)

        server.channels.news_channel = channel

        await ctx.respond(f"Successfully added {channel.name} as the news channel!")

    @commands.slash_command()
    async def add_voting_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        # TODO: Add permissions locks so that only certain roles can add channels

        if ctx.guild and ctx.guild.id not in self.bot.manager:
            self.bot.manager.add_instance(ctx.guild.id, DiscordGameInstance())

        server = self.bot.manager.get_instance(ctx.guild.id)

        server.channels.voting_channel = channel

        await ctx.respond(f"Successfully added {channel.name} as the voting channel!")

    @bridge.bridge_command()
    async def user(self, ctx: bridge.BridgeContext, user: User):
        await ctx.respond(f"User: {user.id}")


def setup(client):
    client.add_cog(Config(client))
