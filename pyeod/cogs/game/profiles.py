from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    FooterPaginator,
    InstanceManager,
    generate_embed_list,
    get_page_limit,
)
from discord import User, Embed
from discord.ext import bridge, commands
from typing import Optional
from pyeod import config


class Profiles(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @bridge.bridge_command(aliases=["prof"])
    @bridge.guild_only()
    async def profile(self, ctx: bridge.Context, *, user: Optional[User] = None):
        server = InstanceManager.current.get_or_create(ctx.guild.id)

        if user is None:
            user = ctx.author

        if user.id in server.db.users:
            logged_in = await server.login_user(user.id)
        else:
            logged_in = None

        embed = Embed(title=user.display_name, color=config.EMBED_COLOR)
        embed.add_field(name="👤User", value=user.mention, inline=False)
        leaderboard_position = (
            sorted(
                server.db.users.keys(),
                key=lambda key: len(server.db.users[key].inv),
                reverse=True,
            ).index(logged_in.id)
            + 1
        )
        async with server.db.user_lock.reader:
            if leaderboard_position == 1:
                embed.add_field(
                    name="🥇Leaderboard Position",
                    value=f"#{leaderboard_position}",
                )
            elif leaderboard_position == 2:
                embed.add_field(
                    name="🥈Leaderboard Position",
                    value=f"#{leaderboard_position}",
                )
            elif leaderboard_position == 3:
                embed.add_field(
                    name="🥉Leaderboard Position",
                    value=f"#{leaderboard_position}",
                )
            else:
                embed.add_field(
                    name="🎖️Leaderboard Position",
                    value=f"#{leaderboard_position}",
                )
            embed.add_field(
                name="🎒Elements Made",
                value=f"{len(logged_in.inv):,}",
            )
            embed.add_field(
                name="🗳️Votes Cast",
                value=f"{logged_in.votes_cast_count:,}",
            )
            embed.add_field(
                name="✍Suggested Combos",
                value=f"{logged_in.created_combo_count:,}",
            )
            if logged_in.last_element:
                embed.add_field(
                    name="🆕Most Recent Element",
                    value=f"{logged_in.last_element.name}",
                )
        embed.set_thumbnail(url=user.avatar.url)

        await ctx.respond(embed=embed)


def setup(client):
    client.add_cog(Profiles(client))
