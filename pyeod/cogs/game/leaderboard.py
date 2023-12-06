from discord.ext import commands, bridge
from discord import User
from typing import Optional
from pyeod.frontend import (
    DiscordGameInstance,
    InstanceManager,
    ElementalBot,
    FooterPaginator,
    generate_embed_list,
    get_page_limit,
)


class Leaderboard(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @bridge.bridge_command(aliases=["leaderboard"])
    @bridge.guild_only()
    async def lb(self, ctx: bridge.Context, *, user: Optional[User] = None):
        server = InstanceManager.current.get_or_create(ctx.guild.id)
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


def setup(client):
    client.add_cog(Leaderboard(client))
