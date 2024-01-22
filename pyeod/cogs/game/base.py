from pyeod.errors import GameError
from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    InstanceManager,
    build_info_embed,
    parse_element_list,
    get_multiplier,
)
from pyeod.utils import format_list
from pyeod import config
from discord import Embed, Message
from discord.commands import option as option_decorator
from discord.ext import bridge, commands
from typing import Union
import random
import functools


def capitalize(name: str) -> str:
    if name.lower() != name:
        return name
    words = [word.capitalize() for word in name.split(" ")]
    return " ".join(words)


class Base(commands.Cog):
    def __init__(self, bot: ElementalBot) -> None:
        self.bot = bot

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
            element = await server.check_element(element_name)
        user = await server.login_user(msg.author.id)

        embed = await build_info_embed(server, element, user)
        await msg.reply(embed=embed)

    async def combine_elements(self, server: DiscordGameInstance, msg: Message) -> None:
        if msg.channel.id not in server.channels.play_channels:
            return
        user = await server.login_user(msg.author.id)
        print(server.combo_limit)

        try:
            if user.last_element is not None:
                last_element_name = user.last_element.name
            else:
                last_element_name = None

            combined_items = parse_element_list(msg.content, "\n")
            elements = []
            if len(combined_items) == 1:
                # No newline found
                if msg.content.startswith("*"):
                    name, count = get_multiplier(msg.content, last_element_name)
                    if name.lower() in server.db.elements:
                        if count > server.combo_limit:
                            raise GameError("Too many elements")
                        elements = [name] * count
                if not len(elements):
                    combined_items = parse_element_list(msg.content)

            if not len(elements):
                # Newlines found or single multiplier failed
                for item in combined_items:
                    if item.lower() in server.db.elements:
                        elements.append(item)
                        continue
                    if item.startswith("*"):
                        name, count = get_multiplier(item, last_element_name)
                        if len(elements) + count > server.combo_limit:
                            raise GameError("Too many elements")
                        elements += [name] * count
                    else:
                        if len(elements) + 1 > server.combo_limit:
                            raise GameError("Too many elements")
                        elements.append(item)
        except GameError:
            await msg.reply(f"🔴 You cannot combine more than {server.combo_limit} elements!")
            return

        if msg.content.startswith("+") and "\n" not in msg.content:
            if user.last_element is None:
                await msg.reply("🔴 Combine something first!")
                return
            elements.insert(0, user.last_element.name)

        if len(elements) == 1 and elements[0].startswith("*"):
            number = elements[0].split(" ", 1)[0][1:]
            if number.isdecimal():
                await msg.reply(f"🔴 Combine something first!")
            else:
                await msg.reply(f"🔴 Invalid multiplier: **{number}**")
            return

        if len(elements) < 2:
            return
        if len(elements) > server.combo_limit:
            await msg.reply(f"🔴 You cannot combine more than {server.combo_limit} elements!")
            return

        notfound = []
        async with server.db.element_lock.reader:
            for i in range(len(elements)):
                if elements[i].startswith("#"):
                    elem_id = elements[i][1:].strip()
                    if elem_id.isdecimal() and int(elem_id) in server.db.elem_id_lookup:
                        elements[i] = server.db.elem_id_lookup[int(elem_id)].name
                    else:
                        notfound.append(elem_id)

        if notfound:
            if len(notfound) == 1:
                await msg.reply(f"🔴 Element ID **{notfound[0]}** doesn't exist!")
            else:
                id_list = [f"**{elem_id}**" for elem_id in notfound]
                await msg.reply(
                    f"🔴 Element IDs {format_list(id_list, 'and')} don't exist!"
                )
            return

        try:
            element = await server.combine(user, tuple(elements))
            await msg.reply(f"🆕 You made **{element.name}**!")
        except GameError as g:
            if g.type == "Already have element":
                # Keep last element
                user.last_combo = ()
                await msg.reply(
                    f"🟦 You made **{g.meta['element'].name}**, but you already have it!"
                )
            elif g.type == "Not a combo":
                # Keep last combo
                user.last_element = None
                await msg.reply(
                    "🟥 Not a combo! Use **!s <element_name>** to suggest an element"
                )
            elif g.type == "Do not exist":
                user.last_element = None
                user.last_combo = ()
                element_list = [f"**{elem}**" for elem in g.meta["elements"]]
                if len(element_list) == 1:
                    await msg.reply(f"🔴 Element {element_list[0]} doesn't exist!")
                else:
                    await msg.reply(
                        f"🔴 Elements {format_list(element_list, 'and')} don't exist!"
                    )
            elif g.type == "Not in inv":
                user.last_element = None
                user.last_combo = ()
                element_list = [f"**{elem.name}**" for elem in g.meta["elements"]]
                await msg.reply(f"🔴 You don't have {format_list(element_list)}!")
        await self.bot.award_achievements(server, msg)

    async def suggest_element(
        self, server: DiscordGameInstance, name: str, msg: Message, autocapitalize: bool
    ) -> None:
        user = await server.login_user(msg.author.id)
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
            return

        combo = user.last_combo
        if autocapitalize:
            name = capitalize(name.strip())
        else:
            name = name.strip()

        if name.startswith("#"):
            await msg.reply("🔴 Element names cannot start with **#**!")
            return
        if "\n" in name:
            await msg.reply("🔴 Element names cannot contain newlines!")
            return
        if "<@" in name:
            await msg.reply("🔴 Element names cannot contain **<@**!")
            return
        # Allow users to do potential dumb formatting shit, but also allow normal use of these strings
        # Backslash escape all fucked up discord shit
        for bad_string in ["\\", "</", "<#", "_", "|", "```", "*", ">", "<:"]:
            name = name.replace(bad_string, f"\\{bad_string}")
        name = name.replace("\u200C", "")# ZWNJ

        if len(name) > 256:
            await msg.reply("🔴 Element names cannot be longer than 256 character!")
            return
        if name == "":
            await msg.reply("🔴 Please give a valid element name!")
            return

        poll = await server.suggest_element(user, combo, name)

        emoji = "🌟" if poll.exists else "✨"
        elements = "** + **".join([i.name for i in combo])
        await self.bot.add_poll(
            server,
            poll,
            msg,
            f"🗳️ Suggested **{elements}** = **{poll.result}**! {emoji}",
        )

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
            await self.suggest_element(server, msg.content[1:], msg, True)
        else:
            await self.combine_elements(server, msg)

    @bridge.bridge_command(aliases=["s"])
    @bridge.guild_only()
    @option_decorator("element_name", required=True)
    async def suggest(
        self, ctx: bridge.Context, *, element_name: str, autocapitalize: bool = True
    ):
        """Suggests a result for an element combo to be voted on"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if ctx.channel.id not in server.channels.play_channels:
            await ctx.respond("🔴 You can only suggest in play channels!")
            return
        # Only required methods of ctx is .author, .channel and .reply
        await self.suggest_element(server, element_name, ctx, autocapitalize)

    @bridge.bridge_command(aliases=["rcom"])
    @bridge.guild_only()
    async def random_combination(
        self, ctx: bridge.Context, number_of_elements: int = 2
    ):
        """Combines random elements from your inventory"""
        if not (1 < number_of_elements <= server.combo_limit):
            await ctx.respond("🔴 Invalid number of elements!")
            return
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = await server.login_user(ctx.author.id)
        combo = []
        async with server.db.element_lock.reader:
            for _ in range(number_of_elements):
                combo.append(server.db.elem_id_lookup[random.choice(user.inv)].name)
        description = (
            f"Combined:\n> \n> **{'** + **'.join(combo)}**\n> \n\nResult:\n> \n> "
        )
        try:
            element = await server.combine(user, tuple(combo))
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


def setup(client):
    client.add_cog(Base(client))
