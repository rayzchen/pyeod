from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    FooterPaginator,
    InstanceManager,
    generate_embed_list,
    get_page_limit,
    create_inventory,
    InventoryPaginator,
)
from pyeod import config
from discord import User, Embed, EmbedField
from discord.ext import bridge, commands
from typing import Optional


class Lists(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @bridge.bridge_command()
    @bridge.guild_only()
    async def inv(self, ctx: bridge.Context, user: Optional[User] = None):
        """Shows your elements"""

        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if user is None:
            user = ctx.author

        pages = await create_inventory("Found", ctx, user)

        paginator = InventoryPaginator(pages, ctx, user)
        await paginator.respond(ctx)

    @bridge.bridge_command()
    @bridge.guild_only()
    async def stats(self, ctx: bridge.Context):
        """Shows the server stats"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        elements = len(server.db.elements)
        combinations = len(server.db.combos)
        users = len(server.db.users)

        found = 0
        cast = 0
        for user in server.db.users.values():
            found += len(user.inv)
            cast += user.votes_cast_count

        embed = Embed(
            color=config.EMBED_COLOR,
            title="Stats",
            fields=[
                EmbedField("🔢 Element Count", f"{elements:,}", True),
                EmbedField("🔄 Combination Count", f"{combinations:,}", True),
                EmbedField("🧑‍🤝‍🧑 User Count", f"{users:,}", True),
                EmbedField("🔍 Elements Found", f"{found:,}", True),
                EmbedField("📁 Elements Categorized", "N/A", True),
                EmbedField("👨‍💻 Commands Used", "N/A", True),
                EmbedField("🗳️ Votes Cast", f"{cast:,}", True),
                EmbedField("❌ Polls Rejected", "N/A", True),
            ],
        )
        await ctx.respond(embed=embed)


def setup(client):
    client.add_cog(Lists(client))
