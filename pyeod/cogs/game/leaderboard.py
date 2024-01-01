from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    LeaderboardPaginator,
    InstanceManager,
    generate_embed_list,
    get_page_limit,
    create_leaderboard,
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
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if user is None:
            user = ctx.author

        pages = await create_leaderboard("Elements Made", ctx, user)

        paginator = LeaderboardPaginator(pages, ctx, user)
        await paginator.respond(ctx)


def setup(client):
    client.add_cog(Leaderboard(client))
