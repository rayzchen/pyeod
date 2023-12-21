from pyeod.errors import GameError
from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    InstanceManager,
    build_info_embed,
    parse_element_list,
)
from pyeod.utils import format_list
from discord import Embed, Message
from discord.commands import option as option_decorator
from discord.ext import bridge, commands
from typing import Union
import random
import functools


class Base(commands.Cog):
    def __init__(self, bot: ElementalBot) -> None:
        self.bot = bot

    @staticmethod
    def handle_errors(func):
        @functools.wraps(func)
        async def inner(self, msg: Message):
            try:
                await func(self, msg)
            except Exception as e:
                context = bridge.BridgeExtContext(message=msg, bot=self.bot, view=None)
                self.bot.dispatch("bridge_command_error", context, e)

        return inner

    @commands.Cog.listener("on_message")
    @handle_errors
    async def message_handler(self, msg: Message):
        if msg.guild is None:
            # Message from a DM channel
            return
        if msg.guild.id not in InstanceManager.current.instances:
            return
        server = InstanceManager.current.instances[msg.guild.id]

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
        if msg.content.startswith("?#"):
            element_id = msg.content[2:].strip()
            if not element_id.isdecimal():
                await msg.reply(f"🔴 Element ID **{element_id}** doesn't exist!")
                return
            if int(element_id) not in server.db.elem_id_lookup:
                await msg.reply(f"🔴 Element ID **{element_id}** doesn't exist!")
                return
            element = server.db.elem_id_lookup[int(element_id)]
        else:
            element_name = msg.content[1:].strip()
            if not element_name:
                return
            element = server.check_element(element_name)
        user = server.login_user(msg.author.id)

        embed = await build_info_embed(server, element, user)
        await msg.reply(embed=embed)

    async def combine_elements(self, server: DiscordGameInstance, msg: Message) -> None:
        if msg.channel.id not in server.channels.play_channels:
            return
        user = server.login_user(msg.author.id)

        elements = []
        if msg.content.startswith("*"):
            number = msg.content.split(" ", 1)[0][1:]
            if number.isdecimal():
                multiplier = min(int(number), 22)
                if " " in msg.content:
                    elements = [msg.content.split(" ", 1)[1]] * multiplier
                elif user.last_element is not None:
                    elements = [user.last_element.name] * multiplier
                else:
                    await msg.reply("🔴 Combine something first!")
                    return
                if len(elements) < 2:
                    await msg.reply("🔴 Please combine at least 2 elements!")
                    return

        if not elements:
            elements = parse_element_list(msg.content)

        if (
            msg.content.startswith("*")
            and len(elements) == 1
            and not multiplier.isdecimal()
        ):
            await msg.reply(f"🔴 Invalid multiplier: **{multiplier}**")

        if msg.content.startswith("+"):
            if user.last_element is None:
                await msg.reply("🔴 Combine something first!")
                return
            elements.insert(0, user.last_element.name)

        if len(elements) < 2:
            return
        if len(elements) > 21:
            await msg.reply("🔴 You cannot combine more than 21 elements!")
            return

        try:
            element = server.combine(user, tuple(i.strip() for i in elements))
            await msg.reply(f"🆕 You made **{element.name}**!")
        except GameError as g:
            if g.type == "Not a combo":
                # Keep last combo
                user.last_element = None
                await msg.reply(
                    "🟥 Not a combo! Use **!s <element_name>** to suggest an element"
                )
            if g.type == "Already have element":
                # Keep last element
                user.last_combo = ()
                await msg.reply(
                    f"🟦 You made **{g.meta['element'].name}**, but you already have it!"
                )
            elif g.type == "Not in inv":
                user.last_element = None
                user.last_combo = ()
                element_list = [f"**{elem.name}**" for elem in g.meta["elements"]]
                await msg.reply(f"🔴 You don't have {format_list(element_list)}!")
            if g.type == "Do not exist":
                user.last_element = None
                user.last_combo = ()
                element_list = [f"**{elem}**" for elem in g.meta["elements"]]
                if len(element_list) == 1:
                    await msg.reply(f"🔴 Element {element_list[0]} doesn't exist!")
                else:
                    await msg.reply(
                        f"🔴 Elements {format_list(element_list, 'and')} don't exist!"
                    )

    @bridge.bridge_command(aliases=["s"])
    @bridge.guild_only()
    @option_decorator("element_name", required=True)
    async def suggest(self, ctx: bridge.Context, *, element_name: str = ""):
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if ctx.channel.id not in server.channels.play_channels:
            await ctx.respond("🔴 You can only suggest in play channels!")
            return
        if element_name == "":
            if ctx.message.content.startswith("="):
                element_name = ctx.message.content[1:].strip()
            if element_name == "":
                await ctx.respond("🔴 Please specify an element name!")
                return
        # Only required methods of ctx is .author, .channel and .reply
        await self.suggest_element(server, element_name, ctx)

    @bridge.bridge_command(aliases=["rc"])
    @bridge.guild_only()
    async def random_combination(
        self, ctx: bridge.Context, number_of_elements: int = 2
    ):
        if not (1 < number_of_elements < 21):
            await ctx.respond("🔴 Invalid number of elements!")
            return
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = server.login_user(ctx.author.id)
        combo = []
        for _ in range(number_of_elements):
            combo.append(server.db.elem_id_lookup[random.choice(user.inv)].name)
        description = (
            f"Combined:\n> \n> **{'** + **'.join(combo)}**\n> \n\nResult:\n> \n> "
        )
        try:
            element = server.combine(user, tuple(combo))
            description += f"🆕 You made **{element.name}**!"
        except GameError as g:
            if g.type == "Not a combo":
                # Keep last combo
                user.last_element = None
                description += (
                    "🟥 Not a combo! Use **!s <element_name>** to suggest an element"
                )
            if g.type == "Already have element":
                # Keep last element
                user.last_combo = ()
                description += (
                    f"🟦 You made **{g.meta['element'].name}**, but you already have it!"
                )
        description += "\n> \u200c"  # ZWNJ
        embed = Embed(
            title="Random Combo", description=description, color=config.EMBED_COLOR
        )
        await ctx.respond(embed=embed)

    async def suggest_element(
        self,
        server: DiscordGameInstance,
        name: str,
        msg: Message,
    ) -> None:
        user = server.login_user(msg.author.id)
        if server.channels.voting_channel is None:
            await msg.reply("🤖 Server not configured, please set voting channel")
            return
        if server.channels.news_channel is None:
            await msg.reply("🤖 Server not configured, please set news channel")
            return
        if msg.channel.id not in server.channels.play_channels:
            await msg.reply("🔴 You can only suggest in play channels!")
            return

        if user.last_combo == ():
            await msg.reply("🔴 Combine something first!")
            return
        elif user.last_element is not None:
            await msg.reply("🔴 That combo already exists!")
        else:
            combo = user.last_combo
            poll = server.suggest_element(user, combo, name.strip())

            emoji = "🌟" if poll.exists else "✨"
            elements = "** + **".join([i.name for i in combo])
            await self.bot.add_poll(
                server,
                poll,
                msg,
                f"🗳️ Suggested **{elements}** = **{poll.result}**! {emoji}",
            )


def setup(client):
    client.add_cog(Base(client))
