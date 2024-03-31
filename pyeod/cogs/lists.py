from pyeod import config
from pyeod.errors import GameError
from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    ElementPaginator,
    FooterPaginator,
    InstanceManager,
    autocomplete_elements,
    generate_embed_list,
    get_page_limit,
)
from discord import Embed, EmbedField, User
from discord.commands import option as option_decorator
from discord.ext import bridge, commands
from typing import Optional
import random, time


class Lists(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @bridge.bridge_command()
    @bridge.guild_only()
    async def inv(self, ctx: bridge.Context):
        time.sleep(random.uniform(2,2.5))
        """Shows your elements"""

        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = ctx.author

        logged_in = await server.login_user(user.id)
        inv = [server.db.elem_id_lookup[e] for e in logged_in.inv]
        title = user.display_name + f"'s Inventory ({len(inv)})"
        paginator = await ElementPaginator.create("Found", ctx, user, inv, title, False)
        await paginator.respond(ctx)

    @bridge.bridge_command()
    @bridge.guild_only()
    async def stats(self, ctx: bridge.Context):
        time.sleep(random.uniform(0,1.5))

        """Shows the server stats"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        elements = len(server.db.elements)
        combinations = len(server.db.combos)
        users = len(server.db.users)
        categorized_element_ids = set()

        found = 0
        cast = 0
        achievements = 0
        for user in server.db.users.values():
            found += len(user.inv)
            cast += user.votes_cast_count
            achievements += len(user.achievements)

        # For some reason this operation slows down the bot
        # But when timed it isn't a significant difference???
        for cat_id, category in server.db.categories.items():
            for element in await category.get_elements(server.db):
                if element.id not in categorized_element_ids:
                    categorized_element_ids.add(element.id)

        embed = Embed(
            color=config.EMBED_COLOR,
            title="Stats",
            fields=[
                EmbedField("🔢 Element Count", f"{elements:,}", True),
                EmbedField("🔍 Elements Found", f"{found:,}", True),
            ],
        )
        await ctx.respond(embed=embed)


def setup(client):
    client.add_cog(Lists(client))
