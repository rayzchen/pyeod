from discord.ext import commands, tasks, bridge, pages
from discord import User
from pyeod.model import InstanceManager
from pyeod.frontend import DiscordGameInstance
from pyeod.utils import format_traceback
from pyeod import config
import traceback
import os


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Loading instance manager")
        manager = InstanceManager()
        # TODO: load manager here?

    @bridge.bridge_command()
    async def user(self, ctx: bridge.BridgeContext, user: User):
        await ctx.respond(f"User: {user.id}")


def setup(client):
    client.add_cog(Config(client))
