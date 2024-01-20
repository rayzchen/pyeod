from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    LeaderboardPaginator,
    InstanceManager,
    create_leaderboard,
    create_element_leaderboard,
    ElementLeaderboardPaginator,
)
from discord import User
from discord.ext import bridge, commands
from typing import Optional


class Leaderboard(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @bridge.bridge_command(aliases=["leaderboard"])
    @bridge.guild_only()
    async def lb(self, ctx: bridge.Context, *, user: Optional[User] = None):
        """Shows the leaderboard of who has the most elements
        Has other sorting options available"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if user is None:
            user = ctx.author

        pages = await create_leaderboard("Elements Made", ctx, user)

        paginator = LeaderboardPaginator(pages, ctx, user)
        await paginator.respond(ctx)

    @bridge.bridge_command(aliases=["element_leaderboard", "elb"])
    @bridge.guild_only()
    async def element_lb(self, ctx: bridge.Context, *, user: Optional[User] = None):
        """Shows the leaderboard of elements with the highest difficulty
        Has other sorting options available"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if user is None:
            user = ctx.author

        pages = await create_element_leaderboard("Tree Size", ctx, user)

        paginator = ElementLeaderboardPaginator(pages, ctx, user)
        await paginator.respond(ctx)


def setup(client):
    client.add_cog(Leaderboard(client))
