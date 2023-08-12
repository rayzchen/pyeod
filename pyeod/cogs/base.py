from discord.ext import commands, bridge
from discord import Message
from pyeod.model import GameError
from pyeod.frontend import DiscordGameInstance, InstanceManager
from pyeod import frontend
from typing import Union
import functools


class Base(commands.Cog):
    def __init__(self, bot: bridge.AutoShardedBot):
        self.bot = bot

    @staticmethod
    def handle_errors(func):
        @functools.wraps(func)
        async def inner(self, msg: Message):
            try:
                await func(self, msg)
            except Exception as e:
                await self.bot.dispatch("command_error", msg, e)

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
        user = server.login_user(msg.author.id)

        elements = []
        if msg.content.startswith("*"):
            multiplier = msg.content.split(" ", 1)[0][1:]
            if multiplier.isdecimal():
                if " " in msg.content:
                    elements = [msg.content.split(" ", 1)[1]] * int(multiplier)
                elif user.last_element is not None:
                    elements = [user.last_element.name] * int(multiplier)
                else:
                    await msg.reply("Combine something first")
                    return

        if not elements:
            elements = frontend.parse_element_list(msg.content)
        if len(elements) < 2:
            return
        if len(elements) > 21:
            await msg.reply("You cannot combine more than 21 elements!")
            return

        try:
            element = server.combine(user, [i.strip() for i in elements])
            await msg.reply(f"You made {element.name}")
        except GameError as g:
            if g.type == "Not a combo":
                # Keep last combo
                user.last_element = None
                await msg.reply(
                    "Not a combo, use !s <element_name> to suggest an element"
                )
            if g.type == "Already have element":
                # Keep last element
                user.last_combo = ()
                await msg.reply(g.message)
            elif g.type == "Not in inv":
                user.last_element = None
                user.last_combo = ()
                await msg.reply(
                    "You don't have one or more of those elements"
                )  # Todo: Fix how vague this is
            if g.type == "Not an element":
                user.last_element = None
                user.last_combo = ()
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
                "Suggested " + " + ".join([i.name for i in combo]) + " = " + poll.result
            )


def setup(client):
    client.add_cog(Base(client))
