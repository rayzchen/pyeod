from discord.ext import commands, bridge
from discord import Message, User
from pyeod.model import GameError
from pyeod.frontend import (
    DiscordGameInstance,
    InstanceManager,
    FooterPaginator,
    generate_embed_list,
    get_page_limit
)
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
                self.bot.dispatch("command_error", msg, e)

        return inner

    @commands.Cog.listener("on_message")
    @handle_errors
    async def message_handler(self, msg: Message):
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
                await msg.reply(f"Element ID **{element_id}** doesn't exist!")
                return
            if int(element_id) not in server.db.elem_id_lookup:
                await msg.reply(f"Element ID **{element_id}** doesn't exist!")
                return
            element = server.db.elem_id_lookup[int(element_id)]
        else:
            element_name = msg.content[1:].strip()
            element = server.check_element(element_name)
        user = server.login_user(msg.author.id)

        embed = await frontend.build_info_embed(server, element, user)
        await msg.reply(embed=embed)

    async def combine_elements(self, server: DiscordGameInstance, msg: Message) -> None:
        if msg.channel.id not in server.channels.play_channels:
            return
        user = server.login_user(msg.author.id)

        elements = []
        if msg.content.startswith("*"):
            multiplier = msg.content.split(" ", 1)[0][1:]
            if multiplier.isdecimal():
                if " " in msg.content:
                    elements = [msg.content.split(" ", 1)[1]] * min(int(multiplier), 22)
                elif user.last_element is not None:
                    elements = [user.last_element.name] * min(int(multiplier), 22)
                else:
                    await msg.reply("Combine something first")
                    return

        if not elements:
            elements = frontend.parse_element_list(msg.content)

        if msg.content.startswith("+"):
            if user.last_element is None:
                await msg.reply("Combine something first")
                return
            elements.insert(0, user.last_element.name)

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
            await ctx.respond("You can only suggest in play channels!")
            return
        await self.suggest_element(server, element_name, ctx)

    async def suggest_element(
        self,
        server: DiscordGameInstance,
        name: str,
        ctx: Union[bridge.BridgeContext, Message],
    ) -> None:
        user = server.login_user(ctx.author.id)
        if server.channels.voting_channel is None:
            await ctx.respond("Server not configured, please set voting channel")
        if server.channels.news_channel is None:
            await ctx.respond("Server not configured, please set news channel")
        if ctx.channel.id not in server.channels.play_channels:
            await ctx.respond("You can only suggest in play channels!")
            return

        if user.last_combo == ():
            await ctx.reply("Combine something first")
            return
        else:
            combo = user.last_combo
            poll = server.suggest_element(user, combo, name)
            if server.vote_req == 0:
                server.check_polls()
                news_channel = await self.bot.fetch_channel(server.channels.news_channel)
                await news_channel.send(poll.get_news_message(server))
            else:
                voting_channel = await self.bot.fetch_channel(server.channels.voting_channel)
                msg = await voting_channel.send(embed = server.convert_poll_to_embed(poll))
                server.poll_msg_lookup[msg.id] = poll
            await ctx.reply(
                "Suggested " + " + ".join([i.name for i in combo]) + " = " + poll.result
            )
            if server.vote_req != 0:#Adding reactions after just feels snappier
                await msg.add_reaction('\u2B06\uFE0F')  # ⬆️ Emoji
                await msg.add_reaction('\u2B07\uFE0F') # ⬇️ Emoji

    @bridge.bridge_command(aliases=["leaderboard"])
    async def lb(self, ctx: bridge.BridgeContext, *, user: User = None):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        if user is None:
            user = ctx.author
        # Don't add new user to db
        if user.id in server.db.users:
            logged_in = server.login_user(user.id)
        else:
            logged_in = None

        lines = []
        user_index = -1
        user_inv = 0
        i = 0
        for user_id, user in sorted(server.db.users.items(), key=lambda pair: len(pair[1].inv), reverse=True):
            i += 1
            if logged_in is not None and user_id == logged_in.id:
                user_index = i
                user_inv = len(user.inv)
                lines.append(f"{i}\. <@{user_id}> *You* - {len(user.inv):,}")
            else:
                lines.append(f"{i}\. <@{user_id}> - {len(user.inv):,}")

        limit = get_page_limit(server, ctx.channel.id)
        pages = generate_embed_list(lines, "Top Most Found", limit)
        if logged_in is not None and user_id == logged_in.id:
            for page in pages:
                if f"<@{user_id}>" not in page.description:
                    page.description += f"\n\n{user_index}\. <@{user_id} *You* - {user_inv:,}"

        paginator = FooterPaginator(pages)
        await paginator.respond(ctx)

def setup(client):
    client.add_cog(Base(client))
