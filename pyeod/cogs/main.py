from discord.ext import commands, tasks # upm packge(pycord)
from pyeod.utils import format_traceback

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
        error = format_traceback(err, False)
        await ctx.send("There was an error processing the command:\n" + error)

    @tasks.loop(seconds=2)
    async def restart_checker(self):
        if os.path.isfile("stop"):
            print("Stopping")
            self.restart_checker.stop()
            await self.bot.close()
        elif os.path.isfile("restart"):
            os.remove("restart")
            print("Restarting")
            self.restart_checker.stop()
            await self.bot.close()