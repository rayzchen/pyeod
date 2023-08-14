from discord.ext import commands, bridge
from discord import Message, User, NotFound
from pyeod.model import GameError, Poll
from pyeod.frontend import (
    DiscordGameInstance,
    InstanceManager,
    FooterPaginator,
    generate_embed_list,
    get_page_limit,
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
                if len(multiplier) > 2:  # Mult above 99
                    await msg.reply("You cannot combine more than 21 elements!")
                    return
                multiplier = int(multiplier)
                if multiplier < 2:
                    return
                if multiplier > 21:
                    await msg.reply("You cannot combine more than 21 elements!")
                    return
                if " " in msg.content:
                    elements = [msg.content.split(" ", 1)[1]] * multiplier
                elif user.last_element is not None:
                    elements = [user.last_element.name] * multiplier
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

    async def add_poll(
        self,
        server: DiscordGameInstance,
        poll: Poll,
        ctx: bridge.BridgeContext,
        suggestion_message: str,
    ):
        if server.vote_req == 0:
            server.check_polls()
            news_channel = await self.bot.fetch_channel(server.channels.news_channel)
            await news_channel.send(poll.get_news_message(server))
        else:
            voting_channel = await self.bot.fetch_channel(
                server.channels.voting_channel
            )
            msg = await voting_channel.send(embed=server.convert_poll_to_embed(poll))
            server.poll_msg_lookup[msg.id] = poll
        await ctx.reply(suggestion_message)
        if server.vote_req != 0:  # Adding reactions after just feels snappier
            await msg.add_reaction("\U0001F53C")  # ⬆️ Emoji
            await msg.add_reaction("\U0001F53D")

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
            await self.add_poll(
                server,
                poll,
                ctx,
                "Suggested "
                + " + ".join([i.name for i in combo])
                + " = "
                + poll.result,
            )

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
        for user_id, user in sorted(
            server.db.users.items(), key=lambda pair: len(pair[1].inv), reverse=True
        ):
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
                    page.description += (
                        f"\n\n{user_index}\. <@{user_id} *You* - {user_inv:,}"
                    )

        paginator = FooterPaginator(pages)
        await paginator.respond(ctx)

    # Don't use bridge command cus params
    @bridge.bridge_command(aliases=["c", "mark", "note"])
    async def comment(
        self, ctx: bridge.BridgeContext, *, marked_element: str, mark: str = None
    ):  # Sneaky use of args here
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        user = server.login_user(ctx.author.id)
        if ctx.is_app:
            if not mark:
                await ctx.respond("Please suggest a mark")
                return
            marked_element = marked_element.lower()
        else:
            split_msg = marked_element.split("|")
            if len(split_msg) < 2:
                await ctx.reply("Please separate each parameter with a |")
                return
            mark = split_msg[1].strip()
        if not server.db.has_element(marked_element):
            await ctx.respond("Not a valid element")
            return
        if len(mark) > 3000:
            await ctx.respond("Marks cannot be over 3000 characters in length")
            return
        element = server.db.elements[marked_element]
        poll = server.suggest_mark(user, element, mark)

        await self.add_poll(
            server, poll, ctx, f"Suggested a new mark for {element.name}!"
        )

    @bridge.bridge_command(aliases=["acol"])
    async def add_collaborators(
        self,
        ctx: bridge.BridgeContext,
        *,
        element: str,
        collaborator1: User = None,
        collaborator2: User = None,
        collaborator3: User = None,
        collaborator4: User = None,
        collaborator5: User = None,
        collaborator6: User = None,
        collaborator7: User = None,
        collaborator8: User = None,
        collaborator9: User = None,
        collaborator10: User = None,
    ):  # Dude fuck slash commands this is the only way to do this (i think)
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        user = server.login_user(ctx.author.id)
        extra_authors = []
        if ctx.is_app:
            element = element.lower()
            element = server.db.elements[element]
            for i in [collaborator1, collaborator2, collaborator3, collaborator4, collaborator5, collaborator6, collaborator7, collaborator8, collaborator9, collaborator10]:
                if i != None and i not in element.extra_authors and element.author and i.id != element.author.id:
                    extra_authors.append(server.login_user(i.id))
        else:
            split_msg = element.split("|")
            if len(split_msg) < 2:
                await ctx.respond("Please separate each parameter with a |")
                return
            element = split_msg[0].lower().strip()
            element = server.db.elements[element]
            for i in split_msg[1].split(" "):
                id = int(i.replace("<@", "").replace(">", ""))
                try:
                    await self.bot.fetch_user(id)
                except NotFound:
                    await ctx.respond("Please only enter valid users, using the @<user> syntax separated by spaces")
                    return
                if i not in element.extra_authors and element.author and i.id != element.author.id and element.author.id:
                    extra_authors.append(server.login_user(id))
        
        if len(extra_authors) == 0:
            await ctx.reply("Please make sure you entered a valid user created element and valid users!")
            return
        if len(extra_authors) + len(element.extra_authors) > 10:
            await ctx.respond("An element cannot have more than 10 collaborators")
            return
        poll = server.suggest_add_collaborators(user, element, extra_authors)
        await self.add_poll(server, poll, ctx, f"Suggested to add those users as collaborators to the element")
    
    @bridge.bridge_command(aliases=["acol"])
    async def add_collaborators(
        self,
        ctx: bridge.BridgeContext,
        *,
        element: str,
        collaborator1: User = None,
        collaborator2: User = None,
        collaborator3: User = None,
        collaborator4: User = None,
        collaborator5: User = None,
        collaborator6: User = None,
        collaborator7: User = None,
        collaborator8: User = None,
        collaborator9: User = None,
        collaborator10: User = None,
    ):  # Dude fuck slash commands this is the only way to do this (i think)
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        user = server.login_user(ctx.author.id)
        extra_authors = []
        if ctx.is_app:
            element = element.lower()
            element = server.db.elements[element]
            for i in [collaborator1, collaborator2, collaborator3, collaborator4, collaborator5, collaborator6, collaborator7, collaborator8, collaborator9, collaborator10]:
                extra_authors.append(i.id)
                    
        else:
            split_msg = element.split("|")
            if len(split_msg) < 2:
                await ctx.respond("Please separate each parameter with a |")
                return
            element = split_msg[0].lower().strip()
            element = server.db.elements[element]
            for i in split_msg[1].split(" "):
                if not i:
                    continue
                id = int(i.replace("<@", "").replace(">", ""))
                try:
                    await self.bot.fetch_user(id)
                except NotFound:
                    await ctx.respond("Please only enter valid users, using the @<user> syntax separated by spaces")
                    return
                extra_authors.append(id)
        authors = []
        for i in extra_authors:
            if i != None and i not in [i.id for i in element.extra_authors] and element.author and i != element.author.id:
                authors.append(server.login_user(i))
    
        if len(authors) == 0:
            await ctx.reply("Please make sure you entered a valid user created element and valid users!")
            return
        if len(authors) + len(element.extra_authors) > 10:
            await ctx.respond("An element cannot have more than 10 collaborators")
            return
        poll = server.suggest_add_collaborators(user, element, authors)
        await self.add_poll(server, poll, ctx, f"Suggested to add those users as collaborators to {element.name}")

    @bridge.bridge_command(aliases=["rcol"])
    async def remove_collaborators(
        self,
        ctx: bridge.BridgeContext,
        *,
        element: str,
        collaborator1: User = None,
        collaborator2: User = None,
        collaborator3: User = None,
        collaborator4: User = None,
        collaborator5: User = None,
        collaborator6: User = None,
        collaborator7: User = None,
        collaborator8: User = None,
        collaborator9: User = None,
        collaborator10: User = None,
    ):  # Dude fuck slash commands this is the only way to do this (i think)
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        user = server.login_user(ctx.author.id)
        extra_authors = []
        if ctx.is_app:
            element = element.lower()
            element = server.db.elements[element]
            for i in [collaborator1, collaborator2, collaborator3, collaborator4, collaborator5, collaborator6, collaborator7, collaborator8, collaborator9, collaborator10]:
                extra_authors.append(i.id)
                    
        else:
            split_msg = element.split("|")
            if len(split_msg) < 2:
                await ctx.respond("Please separate each parameter with a |")
                return
            element = split_msg[0].lower().strip()
            element = server.db.elements[element]
            for i in split_msg[1].strip().split(" "):
                if not i:
                    continue
                id = int(i.replace("<@", "").replace(">", ""))
                try:
                    await self.bot.fetch_user(id)
                except NotFound:
                    await ctx.respond("Please only enter valid users, using the @<user> syntax separated by spaces")
                    return
                extra_authors.append(id)
        authors = []
        for i in extra_authors:
            if i != None and i in [i.id for i in element.extra_authors] and element.author and i != element.author.id:
                authors.append(server.login_user(i))
    
        if len(authors) == 0:
            await ctx.reply("Please make sure you entered a valid user created element and valid users already in the collaboration!")
            return
        poll = server.suggest_remove_collaborators(user, element, authors)
        await self.add_poll(server, poll, ctx, f"Suggested to remove those users as collaborators to {element.name}")

def setup(client):
    client.add_cog(Base(client))
