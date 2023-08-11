from discord.ext import commands, tasks, bridge, pages
from discord.utils import get
from discord import User, Message
from pyeod.utils import format_traceback
from pyeod.model import GameError
from pyeod.frontend import DiscordGameInstance
from pyeod import config
import traceback
import os


class Main(commands.Cog):
    def __init__(self, bot):
        self.bot: bridge.AutoShardedBot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is ready")
        print("Logged in as:", self.bot.user)
        print("ID:", self.bot.user.id)
        self.restart_checker.start()

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, err: commands.errors.CommandError
    ):
        # Handle different exceptions from parsing arguments here
        if isinstance(err, commands.errors.UserNotFound):
            await ctx.send(str(err))
        else:
            print(
                "".join(traceback.format_exception(type(err), err, err.__traceback__))
            )
            error = format_traceback(err)
            await ctx.send("There was an error processing the command:\n" + error)

    @bridge.bridge_command(aliases=["ms"])
    async def ping(self, ctx: bridge.BridgeContext):
        await ctx.respond(f"Pong {round(self.bot.latency*1000)}ms")

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

    @commands.Cog.listener("on_message")
    async def combine_elements(self, msg: Message):
        try:  # Make sure manager is actually initialized
            self.bot.manager
        except AttributeError:
            return

        server: DiscordGameInstance = self.bot.manager.get_instance(
            msg.guild.id
        )  # Intellisense not working so extra annotation

        if (
            await self.bot.fetch_channel(msg.channel.id)
            not in server.channels.play_channels
        ):
            return

        if msg.author.bot:  # No bots in eod
            return

        if msg.content.startswith("!"):
            return

        elements = []
        if len(msg.content.split("\n")) > 1:
            elements = msg.content.split("\n")
        else:
            #! TEMP COMBO PARSING SOLUTION
            # Will change to be more robust later, works for now
            elements = msg.content.split(",")

        user = server.login_user(msg.author.id)
        try:
            element = server.combine(user, [i.strip() for i in elements])
            await msg.reply(f"You made {element.name}")
        except GameError as g:
            if g.type == "Not a combo":
                await msg.reply(
                    "Not a combo, use !s <element_name> to suggest an element"
                )
            if g.type == "Already have element":
                await msg.reply(g.message)
            if g.type == "Not in inv":
                await msg.reply(
                    "You don't have one or more of those elements"
                )  # Todo: Fix how vague this is
            if g.type == "Not an element":
                await msg.reply("Not a valid element")

    @bridge.bridge_command(aliases=["s"])
    async def suggest(self, ctx: bridge.BridgeContext, *, element_name: str):
        try:  # Make sure manager is actually initialized
            self.bot.manager
        except AttributeError:
            return

        server: DiscordGameInstance = self.bot.manager.get_instance(ctx.guild.id)

        if (
            await self.bot.fetch_channel(ctx.channel.id)
            not in server.channels.play_channels
        ):
            return

        user = server.login_user(ctx.author.id)

        if user.last_combo == ():
            await ctx.reply("Combine something first")
            return
        else:
            #! ANARCHY VOTING
            p = server.suggest_element(
                user, [i.name for i in user.last_combo], element_name
            )
            p.votes += 5
            server.check_polls()
            await ctx.reply(
                " + ".join([i.name for i in user.last_combo]) + " = " + element_name
            )


def setup(client):
    client.add_cog(Main(client))
