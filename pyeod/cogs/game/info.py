from pyeod import config
from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    InstanceManager,
    autocomplete_elements,
)
from pyeod.model import (
    AddCollabPoll,
    ColorPoll,
    IconPoll,
    ImagePoll,
    MarkPoll,
    RemoveCollabPoll,
)
from discord import Attachment, NotFound, User
from discord.commands import option as option_decorator
from discord.ext import bridge, commands
import aiohttp
from typing import Optional
import re


class Info(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    def check_color(self, color: str) -> bool:
        if not len(color) == 6:
            return False
        numbers = "0123456789abcdef"
        if not all(x.lower() in numbers for x in color):
            return False
        return True

    @bridge.bridge_command(aliases=["m", "comment", "note"])
    @bridge.guild_only()
    @option_decorator("marked_element", autocomplete=autocomplete_elements)
    async def mark(self, ctx: bridge.Context, *, marked_element: str, mark: str = ""):
        """Adds a mark to an element
        The text will be displayed on the element's info page"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = await server.login_user(ctx.author.id)
        if ctx.is_app:
            if not mark:
                await ctx.respond("🔴 Please suggest a mark!")
                return
            marked_element = marked_element.lower()
        else:
            split_msg = marked_element.split("|", 1)
            if len(split_msg) < 2:
                await ctx.respond(
                    "🔴 Please separate the element and the mark with a | !"
                )
                return
            marked_element = split_msg[0].strip()
            mark = split_msg[1].strip()
        if not await server.db.has_element(marked_element):
            await ctx.respond("🔴 Not a valid element!")
            return
        if len(mark) > 3000:
            await ctx.respond("🔴 Marks cannot be over 3000 characters in length!")
            return
        element = server.db.elements[marked_element]
        poll = await server.suggest_poll(MarkPoll(user, element, mark))

        await self.bot.add_poll(
            server, poll, ctx, f"🗳️ Suggested a new mark for {element.name}!"
        )

    @bridge.bridge_command(aliases=["c"])
    @bridge.guild_only()
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def color(self, ctx: bridge.Context, *, element: str, color: str = ""):
        """Adds a color to an element
        The color will be put on the element's info page"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if not ctx.is_app:
            element, color = element.rsplit("|", 1)
        user = await server.login_user(ctx.author.id)
        elem = await server.check_element(element.strip())
        color = color.strip()
        if color.startswith("#"):
            color = color[1:]
        if not self.check_color(color):
            await ctx.respond("🔴 Invalid hex code!")
            return
        poll = await server.suggest_poll(ColorPoll(user, elem, "#" + color))

        await self.bot.add_poll(
            server, poll, ctx, f"🗳️ Suggested a new color for {elem.name}!"
        )

    async def check_image_link(self, url):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.head(url, allow_redirects=True) as response:
                    if (
                        200 <= response.status < 300
                        and response.headers["Content-Type"] in config.IMAGE_TYPES
                    ):
                        return True
                    else:
                        return False
            except:
                return False

    @bridge.bridge_command()
    @bridge.guild_only()
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def image(
        self, ctx: bridge.Context, *, element: str, image: Optional[Attachment] = None
    ):
        """Adds an image to an element
        The image will be displayed on the element's info page"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if not ctx.is_app:
            if not ctx.message.attachments:
                element, image_link = element.rsplit("|", 1)
                element = element.strip()
                if not await self.check_image_link(image_link.strip()):
                    await ctx.respond("🔴 Invalid image link!")
                    return
            else:
                if ctx.message.attachments[0].content_type in config.IMAGE_TYPES:
                    image_link = ctx.message.attachments[0].url
                else:
                    await ctx.respond("🔴 Invalid image!")
                    return
        else:
            await ctx.respond("🔴 You cannot use this command as a slash command!", ephemeral = True)
            return

        user = await server.login_user(ctx.author.id)
        elem = await server.check_element(element)

        poll = await server.suggest_poll(ImagePoll(user, elem, image_link.strip()))

        await self.bot.add_poll(
            server, poll, ctx, f"🗳️ Suggested a new image for {elem.name}!"
        )

    @bridge.bridge_command()
    @bridge.guild_only()
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def icon(
        self, ctx: bridge.Context, *, element: str, icon: Optional[Attachment] = None
    ):
        """Adds an icon to an element
        The icon will be displayed beside the element name on the element's info page"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if not ctx.is_app:
            if not ctx.message.attachments:
                element, icon_link = element.rsplit("|", 1)
                if not await self.check_image_link(icon_link.strip()):
                    await ctx.respond("🔴 Invalid image link!")
                    return
            else:
                if ctx.message.attachments[0].content_type in config.IMAGE_TYPES:
                    icon_link = ctx.message.attachments[0].url
                else:
                    await ctx.respond("🔴 Invalid image!")
                    return
        else:
            await ctx.respond("🔴 You cannot use this command as a slash command!", ephemeral = True)
            return

        user = await server.login_user(ctx.author.id)
        elem = await server.check_element(element)

        poll = await server.suggest_poll(IconPoll(user, elem, icon_link.strip()))

        await self.bot.add_poll(
            server, poll, ctx, f"🗳️ Suggested a new icon for {elem.name}!"
        )

    @bridge.bridge_command(aliases=["acol"])
    @bridge.guild_only()
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def add_collaborators(
        self,
        ctx: bridge.Context,
        *,
        element: str,
        collaborator1: Optional[User] = None,
        collaborator2: Optional[User] = None,
        collaborator3: Optional[User] = None,
        collaborator4: Optional[User] = None,
        collaborator5: Optional[User] = None,
        collaborator6: Optional[User] = None,
        collaborator7: Optional[User] = None,
        collaborator8: Optional[User] = None,
        collaborator9: Optional[User] = None,
        collaborator10: Optional[User] = None,
    ):  # Dude fuck slash commands this is the only way to do this (i think)
        """Adds collaborators to the element
        The collaborators will be displayed on the elements info page"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = await server.login_user(ctx.author.id)
        extra_authors = []
        if ctx.is_app:
            elem = await server.check_element(element)
            for i in [
                collaborator1,
                collaborator2,
                collaborator3,
                collaborator4,
                collaborator5,
                collaborator6,
                collaborator7,
                collaborator8,
                collaborator9,
                collaborator10,
            ]:
                if i:
                    extra_authors.append(i.id)

        else:
            split_msg = element.split("|")
            if len(split_msg) < 2:
                await ctx.respond("🔴 Please separate each parameter with a | !")
                return
            elem = await server.check_element(split_msg[0].strip())
            for i in (
                split_msg[1]
                .strip()
                .replace(",", " ")
                .replace("|", " ")
                .replace("  ", " ")
                .replace("  ", " ")
                .split(" ")
            ):
                if not i:
                    continue
                id = int(i.replace("<@", "").replace(">", ""))
                try:
                    await self.bot.fetch_user(id)
                except NotFound:
                    await ctx.respond(
                        "\U0001F534 Please only enter valid users, using the @<user> syntax separated by spaces!"
                    )
                    return
                extra_authors.append(id)
        authors = []
        for i in extra_authors:
            if (
                i not in [i.id for i in elem.extra_authors]
                and elem.author
                and i != elem.author.id
                and i not in authors
                and i != self.bot.user.id
            ):
                authors.append(await server.login_user(i))

        if len(authors) == 0:
            await ctx.respond(
                "\U0001F534 Please make sure you entered a valid user created element and valid users!"
            )
            return
        if len(authors) + len(elem.extra_authors) > 10:
            await ctx.respond("🔴 You can only add 10 collaborators!")
            return
        poll = await server.suggest_poll(AddCollabPoll(user, elem, tuple(authors)))
        await self.bot.add_poll(
            server,
            poll,
            ctx,
            f"🗳️ Suggested to add those users as collaborators to {elem.name}!",
        )

    @bridge.bridge_command(aliases=["rcol"])
    @bridge.guild_only()
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def remove_collaborators(
        self,
        ctx: bridge.Context,
        *,
        element: str,
        collaborator1: Optional[User] = None,
        collaborator2: Optional[User] = None,
        collaborator3: Optional[User] = None,
        collaborator4: Optional[User] = None,
        collaborator5: Optional[User] = None,
        collaborator6: Optional[User] = None,
        collaborator7: Optional[User] = None,
        collaborator8: Optional[User] = None,
        collaborator9: Optional[User] = None,
        collaborator10: Optional[User] = None,
    ):  # Dude fuck slash commands this is the only way to do this (i think)
        """Removes collaborators from an element
        The collaborators will be displayed on the elements info page"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = await server.login_user(ctx.author.id)
        extra_authors = []
        if ctx.is_app:
            elem = await server.check_element(element)
            for i in [
                collaborator1,
                collaborator2,
                collaborator3,
                collaborator4,
                collaborator5,
                collaborator6,
                collaborator7,
                collaborator8,
                collaborator9,
                collaborator10,
            ]:
                if i:
                    extra_authors.append(i.id)

        else:
            split_msg = element.split("|")
            if len(split_msg) < 2:
                await ctx.respond("🔴 Please separate each parameter with a | !")
                return
            elem = await server.check_element(split_msg[0].strip())
            for i in (
                split_msg[1].strip().replace(",", " ").replace("|", " ").split(" ")
            ):
                if not i:
                    continue
                id = int(i.replace("<@", "").replace(">", ""))
                try:
                    await self.bot.fetch_user(id)
                except NotFound:
                    await ctx.respond(
                        "\U0001F534 Please only enter valid users, using the @<user> syntax separated by spaces!"
                    )
                    return
                extra_authors.append(id)
        authors = []
        for i in extra_authors:
            if (
                i in [i.id for i in elem.extra_authors]
                and elem.author
                and i != elem.author.id
                and i not in authors
                and i != self.bot.user.id
            ):
                authors.append(await server.login_user(i))

        if len(authors) == 0:
            await ctx.respond(
                "\U0001F534 Please make sure you entered a valid user created element and valid users already in the collaboration!"
            )
            return
        poll = await server.suggest_poll(RemoveCollabPoll(user, elem, tuple(authors)))
        await self.bot.add_poll(
            server,
            poll,
            ctx,
            f"🗳️ Suggested to remove those users as collaborators to {elem.name}!",
        )


def setup(client):
    client.add_cog(Info(client))
