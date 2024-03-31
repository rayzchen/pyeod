from pyeod import config
from pyeod.errors import GameError
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
import time, random


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
        time.sleep(random.uniform(0,1.5))
        """Adds a mark to an element
        The text will be displayed on the element's info page"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = await server.login_user(ctx.author.id)
        if ctx.is_app:
            if not mark:
                raise GameError("Null parameter", "Please provide a mark")
            marked_element = marked_element.lower()
        else:
            split_msg = marked_element.split("|", 1)
            if len(split_msg) < 2:
                raise GameError(
                    "Invalid Separator",
                    "Please separate the element and the mark with a | ",
                )
            marked_element = split_msg[0].strip()
            mark = split_msg[1].strip()
        element = await server.get_element_by_str(user, marked_element)
        if len(mark) > 3000:
            raise GameError(
                "Too long", "Mark cannot be over 3000 characters in length"
            )
        poll = await server.suggest_poll(MarkPoll(user, element, mark))

        await self.bot.add_poll(
            server, poll, ctx, f"Suggested a new mark for {element.name}"
        )

    @bridge.bridge_command(aliases=["img"])
    @bridge.guild_only()
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def image(
        self, ctx: bridge.Context, *, element: str, image: Optional[Attachment] = None
    ):
        time.sleep(random.uniform(0,1.5))
        """Adds an image to an element
        The image will be displayed on the element's info page"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if not ctx.is_app:
            if not ctx.message.attachments:
                element, image_link = element.rsplit("|", 1)
                element = element.strip()
                if not await self.check_image_link(image_link.strip()):
                    raise GameError("Cannot cast", "Invalid image link")
            else:
                if ctx.message.attachments[0].content_type in config.IMAGE_TYPES:
                    image_link = ctx.message.attachments[0].url
                else:
                    raise GameError("Cannot cast", "Invalid image")
        else:
            raise GameError(
                "No slash", "You cannot use this command as a slash command"
            )

        user = await server.login_user(ctx.author.id)
        elem = await server.get_element_by_str(user, element.strip())

        poll = await server.suggest_poll(ImagePoll(user, elem, image_link.strip()))

        await self.bot.add_poll(
            server, poll, ctx, f"Suggested a new image for {elem.name}"
        )

def setup(client):
    client.add_cog(Info(client))
