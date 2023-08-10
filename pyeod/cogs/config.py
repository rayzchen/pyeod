from discord.ext import commands, tasks, bridge, pages
from discord import User, Message
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

    @bridge.bridge_command()
    async def user(self, ctx: bridge.BridgeContext, user: User):
        await ctx.respond(f"User: {user.id}")
    
    


def setup(client):
    client.add_cog(Config(client))
