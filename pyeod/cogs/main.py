from discord.ext import commands, tasks, bridge
from pyeod.utils import format_traceback
from pyeod import config
import os

class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is ready")
        print("Logged in as:", self.bot.user)
        print("ID:", self.bot.user.id)
        self.restart_checker.start()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, err):
        error = format_traceback(err)
        await ctx.send("There was an error processing the command:\n" + error)

    @bridge.bridge_command(aliases = ["ms"])
    async def ping(self, ctx):
        await ctx.respond(f'Pong {round(self.bot.latency*1000)}ms')
    
    @tasks.loop(seconds=2)
    async def restart_checker(self):
        if os.path.isfile(config.stopfile):
            print("Stopping")
            # Let main detect stopfile
            self.restart_checker.stop()
            await self.bot.close()
        elif os.path.isfile(config.restartfile):
            os.remove(config.restartfile)
            print("Restarting")
            self.restart_checker.stop()
            await self.bot.close()


def setup(client):
    client.add_cog(Main(client))
