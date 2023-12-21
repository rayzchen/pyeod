from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    FooterPaginator,
    InstanceManager,
    generate_embed_list,
    get_page_limit,
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
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if user is None:
            user = ctx.author
        elif user.id not in server.db.users:
            # If user was None, this shouldn't run
            await ctx.respond("🔴 User not found!")
            return

        logged_in = server.login_user(user.id)
        elements = [server.db.elem_id_lookup[elem].name for elem in logged_in.inv]
        title = user.display_name + f"'s Inventory ({len(logged_in.inv)})"

        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(elements, title, limit)
        paginator = FooterPaginator(embeds)
        await paginator.respond(ctx)

    @bridge.bridge_command()
    @bridge.guild_only()
    async def stats(self, ctx: bridge.Context):
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        elements = len(server.db.elements)
        combinations = len(server.db.combos)
        users = len(server.db.users)

        found = 0
        for user in server.db.users.values():
            found += len(user.inv)

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
                EmbedField("🗳️ Votes Cast", "N/A", True),
                EmbedField("❌ Polls Rejected", "N/A", True),
            ]
        )
        await ctx.respond(embed=embed)

def setup(client):
    client.add_cog(Lists(client))
