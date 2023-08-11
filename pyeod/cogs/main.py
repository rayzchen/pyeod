from discord.ext import commands, tasks, bridge, pages
from discord.utils import get
from discord import User, Message
from pyeod.utils import format_traceback
from pyeod.model import GameError
from pyeod.frontend import DiscordGameInstance, InstanceManager
from pyeod import config, frontend
from typing import Union
import functools
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
            await ctx.channel.send(str(err))
        else:
            print(
                "".join(traceback.format_exception(type(err), err, err.__traceback__)),
                end=""
            )
            if err.__cause__ is not None:
                err = err.__cause__
            error = format_traceback(err)
            await ctx.channel.send("There was an error processing the command:\n" + error)

    @bridge.bridge_command(aliases=["ms"])
    async def ping(self, ctx: bridge.BridgeContext):
        await ctx.respond(f"Pong {round(self.bot.latency*1000)}ms")

    @bridge.bridge_command()
    async def clear_polls(self, ctx: bridge.BridgeContext):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        server.db.polls.clear()
        # TODO: delete polls and notify in news
        await ctx.reply("Cleared polls!")

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

    @staticmethod
    def handle_errors(func):
        @functools.wraps(func)
        async def inner(self, msg: Message):
            try:
                await func(self, msg)
            except Exception as e:
                await self.on_command_error(msg, e)
        return inner

    @commands.Cog.listener("on_message")
    @handle_errors
    async def message_handler(self, msg: Message):
        server = InstanceManager.current.get_or_create(
            msg.guild.id, DiscordGameInstance
        )
        if msg.channel.id not in server.channels.play_channels:
            return
        if msg.author.bot:  # No bots in eod
            return
        if msg.content.startswith("!"):
            return

        if msg.content.startswith("?"):
            await self.show_element_info(server, msg)
        elif msg.content.startswith("="):
            await self.suggest_element(server, msg.content[1:], msg)
        else:
            await self.combine_elements(server, msg)

    async def show_element_info(
        self, server: DiscordGameInstance, msg: Message
    ) -> None:
        element_name = msg.content[1:].strip()
        element = server.check_element(element_name)
        user = server.login_user(msg.author.id)

        embed = await frontend.build_info_embed(self.bot, element, user)
        await msg.reply(embed=embed)

    async def combine_elements(self, server: DiscordGameInstance, msg: Message) -> None:
        elements = frontend.parse_element_list(msg.content)
        if len(elements) < 2:
            return
        if len(elements) > 21:
            await msg.reply("You cannot combine more than 21 elements!")
            return

        user = server.login_user(msg.author.id)
        try:
            element = server.combine(user, [i.strip() for i in elements])
            await msg.reply(f"You made {element.name}")
        except GameError as g:
            if g.type == "Not a combo":
                await msg.reply(
                    "Not a combo, use !s <element_name> to suggest an element"
                )
            else:
                user.last_combo = ()
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
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        if ctx.channel.id not in server.channels.play_channels:
            return
        await self.suggest_element(server, element_name, ctx)

    async def suggest_element(
        self,
        server: DiscordGameInstance,
        name: str,
        ctx: Union[bridge.BridgeContext, Message],
    ) -> None:
        user = server.login_user(ctx.author.id)

        if user.last_combo == ():
            await ctx.reply("Combine something first")
            return
        else:
            combo = user.last_combo
            poll = server.suggest_element(user, combo, name)
            if server.vote_req == 0:
                server.check_polls()
            else:
                # TODO: post poll message
                pass
            await ctx.reply(
                "Suggested "
                + " + ".join([i.name for i in combo])
                + " = "
                + poll.result
            )


def setup(client):
    client.add_cog(Main(client))
