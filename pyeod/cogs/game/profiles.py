from pyeod import config
from pyeod.frontend import ElementalBot, InstanceManager
from pyeod.model.types import GameError
from discord import Embed, User
from discord.ext import bridge, commands
from typing import Optional


class Profiles(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @bridge.bridge_command(aliases=["prof"])
    @bridge.guild_only()
    async def profile(self, ctx: bridge.Context, *, user: Optional[User] = None):
        """Shows your profile and your own personal stats"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)

        if user is None:
            user = ctx.author

        logged_in: User = await server.login_user(user.id)

        embed = Embed(title=user.display_name, color=config.EMBED_COLOR)
        embed.add_field(
            name=f"{server.get_icon(logged_in.icon)} User",
            value=user.mention,
            inline=False,
        )
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
                    name="🥇 Leaderboard Position",
                    value=f"#{leaderboard_position}",
                )
            elif leaderboard_position == 2:
                embed.add_field(
                    name="🥈 Leaderboard Position",
                    value=f"#{leaderboard_position}",
                )
            elif leaderboard_position == 3:
                embed.add_field(
                    name="🥉 Leaderboard Position",
                    value=f"#{leaderboard_position}",
                )
            else:
                embed.add_field(
                    name="🎖️ Leaderboard Position",
                    value=f"#{leaderboard_position}",
                )
            embed.add_field(
                name="🎒 Elements Made",
                value=f"{len(logged_in.inv):,}",
            )
            embed.add_field(
                name="🗳️ Votes Cast",
                value=f"{logged_in.votes_cast_count:,}",
            )
            embed.add_field(
                name="✍️ Suggested Combos",
                value=f"{logged_in.created_combo_count:,}",
            )
            embed.add_field(
                name="🏆 Achievements",
                value=f"{len(logged_in.achievements)}",
            )
            if logged_in.achievements:
                embed.add_field(
                    name="🌟 Latest Achievement",
                    value=f"{await server.get_achievement_name(logged_in.achievements[-1])}",
                )
            if logged_in.last_element:
                embed.add_field(
                    name="🆕 Most Recent Element",
                    value=f"{logged_in.last_element.name}",
                )
        embed.set_thumbnail(url=user.avatar.url)

        await ctx.respond(embed=embed)

    @bridge.bridge_command(aliases=["ui"])
    @bridge.guild_only()
    async def user_icon(self, ctx: bridge.Context, *, icon_emoji: str):
        """Sets your icon that will appear next to your name"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)

        logged_in: User = await server.login_user(ctx.author.id)

        try:
            icon_id = server.get_icon_by_emoji(icon_emoji)
        except KeyError:
            raise GameError("Not an icon", "Not an icon!")

        await server.set_icon(logged_in, icon_id)

        await ctx.respond(f"✨ Successfully set {icon_emoji} as your icon")


def setup(client):
    client.add_cog(Profiles(client))
