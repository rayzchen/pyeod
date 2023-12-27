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

        embed = Embed(title=user.display_name)
        embed.add_field(name="User", value=user.mention, inline=False)
        async with server.db.user_lock.reader:
            i = 0
            for user_id, _user in sorted(
                server.db.users.items(), key=lambda pair: len(pair[1].inv), reverse=True
            ):
                i += 1
                if logged_in is not None and user_id == logged_in.id:
                    embed.add_field(
                        name="Leaderboard Position", value=f"#{i}"
                    )
                    embed.add_field(
                        name="Elements Made",
                        value=f"{len(logged_in.inv):,}",
                    )
                    embed.add_field(
                        name="Votes Cast",
                        value=f"{logged_in.votes_cast_count:,}",
                    )
                    embed.add_field(
                        name="Suggested Combos",
                        value=f"{logged_in.created_combo_count:,}",
                    )
                    if logged_in.last_element:
                        embed.add_field(
                            name="Most Recent Element",
                            value=f"{logged_in.last_element.name}",
                        )
                    break
        embed.set_thumbnail(url=user.avatar.url)

        await ctx.respond(embed=embed)


def setup(client):
    client.add_cog(Profiles(client))
