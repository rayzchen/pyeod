from pyeod import config
from pyeod.errors import GameError
from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    InstanceManager,
    autocomplete_categories,
    build_info_embed,
    get_multiplier,
    parse_element_list,
)
from pyeod.utils import format_list
from discord import Embed, Message
from discord.ext.bridge import bridge_option as option_decorator
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
        element_str = msg.content[1:].strip()
        if element_str == "":
            return
        user = await server.login_user(msg.author.id)

        embed = await build_info_embed(
            server, await server.get_element_by_str(user, element_str), user
        )
        await msg.reply(embed=embed)

    async def combine_elements(self, server: DiscordGameInstance, msg: Message) -> None:
        if msg.channel.id not in server.channels.play_channels:
            return
        user = await server.login_user(msg.author.id)

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
                        raise GameError(
                            "Too many elements",
                            f"You cannot combine more than {server.combo_limit} elements!",
                        )
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
                        raise GameError(
                            "Too many elements",
                            f"You cannot combine more than {server.combo_limit} elements!",
                        )
                    elements += [name] * count
                else:
                    if len(elements) + 1 > server.combo_limit:
                        raise GameError(
                            "Too many elements",
                            f"You cannot combine more than {server.combo_limit} elements!",
                        )
                    elements.append(item)

        if msg.content.startswith("+") and "\n" not in msg.content:
            if user.last_element is None:
                raise GameError("No previous element", "Combine something first!")
            elements.insert(0, user.last_element.name)

        if len(elements) == 1 and elements[0].startswith("*"):
            number = elements[0].split(" ", 1)[0][1:]
            if number.isdecimal():
                raise GameError("No previous element", "Combine something first!")
            else:
                raise GameError("Invalid mult", f"Invalid multiplier: {number}!")
            return

        if len(elements) < 2:
            return
        if len(elements) > server.combo_limit:
            raise GameError(
                "Too many elements",
                f"You cannot combine more than {server.combo_limit} elements!",
            )
            return

        notfound = []
        async with server.db.element_lock.reader:
            for i in range(len(elements)):
                if elements[i].startswith("#"):
                    elem_id = elements[i][1:].strip()
                    # Reserved keywords
                    if elem_id in ["last", "random", "randomininv"]:
                        continue
                    if elem_id.isdecimal() and int(elem_id) in server.db.elem_id_lookup:
                        elements[i] = server.db.elem_id_lookup[int(elem_id)].name
                    else:
                        notfound.append(elem_id)

        if notfound:
            if len(notfound) == 1:
                raise GameError(
                    "Element id does not exist",
                    f"Element with ID **#{notfound[0]}** doesn't exist!",
                )
            else:
                id_list = [f"**{elem_id}**" for elem_id in notfound]
                raise GameError(
                    "Element ids don't exist",
                    f"Element IDs {format_list(id_list, 'and')} don't exist!",
                )

        element = await server.combine(user, tuple(elements))
        await msg.reply(f"🆕 You made **{element.name}**!")
        # await self.bot.award_achievements(server, msg)

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
            raise GameError(
                "Not a play channel", "You can only suggest in play channels!"
            )

        if user.last_combo == ():
            raise GameError("No previous element", "Combine something first!")
        elif user.last_element is not None:
            raise GameError("Combo already exists", "That combo already exists!")

        combo = user.last_combo
        if autocapitalize:
            name = capitalize(name.strip())
        else:
            name = name.strip()

        if name.startswith("#"):
            raise GameError(
                "Invalid element name", "Element names cannot start with **#**!"
            )
        if "\n" in name:
            raise GameError(
                "Invalid element name", "Element names cannot contain newlines!"
            )
        if "<@" in name:
            raise GameError(
                "Invalid element name", "Element names cannot contain **<@**!"
            )
        # Allow users to do potential dumb formatting shit, but also allow normal use of these strings
        # Backslash escape all fucked up discord shit
        for bad_string in ["\\", "</", "<#", "_", "|", "```", "*", ">", "<:", "<sound"]:
            name = name.replace(bad_string, f"\\{bad_string}")
        name = name.replace("\u200C", "")  # ZWNJ

        if len(name) > 256:
            raise GameError(
                "Invalid element name",
                "Element names cannot be longer than 256 characters!",
            )
        if name == "":
            raise GameError("Invalid element name", "Please give a valid element name!")

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
        self, ctx: bridge.BridgeContext, *, element_name: str, autocapitalize: bool = True
    ):
        """Suggests a result for an element combo to be voted on"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if ctx.channel.id not in server.channels.play_channels:
            raise GameError("Not a play channel", "This channel is not a play channel!")
        # Only required methods of ctx is .author, .channel and .reply
        await self.suggest_element(server, element_name, ctx, autocapitalize)

    @bridge.bridge_command(aliases=["rcom"])
    @bridge.guild_only()
    @option_decorator("category", autocomplete=autocomplete_categories)
    async def random_combination(
        self,
        ctx: bridge.BridgeContext,
        number_of_elements: int = 2,
        *,
        category: str = None,
    ):
        """Combines random elements from your inventory"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = await server.login_user(ctx.author.id)
        combo = []
        if not (1 < number_of_elements <= server.combo_limit):
            raise GameError(
                "Invalid number of elements",
                f"Number of elements must be between 2 and {server.combo_limit}",
            )
        async with server.db.element_lock.reader:
            if category is None:
                for _ in range(number_of_elements):
                    combo.append(server.db.elem_id_lookup[random.choice(user.inv)].name)
            else:
                async with server.db.category_lock.reader:
                    if category.lower().strip() in server.db.categories:
                        possible_elements = set(
                            [server.db.elem_id_lookup[i] for i in user.inv]
                        ) & set(
                            await server.db.categories[
                                category.lower().strip()
                            ].get_elements(server.db)
                        )
                        combo = [
                            random.sample(possible_elements, 1)[0].name
                            for _ in range(number_of_elements)
                        ]
                    else:
                        raise GameError(
                            "Category does not exist",
                            f"Category **{category}** doesn't exist!",
                            {"category": category},
                        )
        description = (
            f"Combined:\n> \n> **{'** + **'.join(combo)}**\n> \n\nResult:\n> \n> "
        )
        try:
            element = await server.combine(user, tuple(combo))
            description += f"🆕 You made **{element.name}**!"
        except GameError as g:
            if "emoji" not in g.meta:
                description += f"🔴 {g.message}"
            else:
                description += f"{g.meta['emoji']} {g.message}"
        description += "\n> \u200c"  # ZWNJ
        embed = Embed(
            title="Random Combo", description=description, color=config.EMBED_COLOR
        )
        await ctx.respond(embed=embed)


def setup(client):
    client.add_cog(Base(client))
