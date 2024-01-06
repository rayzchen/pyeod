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
    async def achievements(self, ctx: bridge.Context, user: Optional[User] = None):
        """Shows earned achievements"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if user is None:
            user = ctx.author
        elif user.id not in server.db.users:
            # If user was None, this shouldn't run
            await ctx.respond("🔴 User not found!")
            return

        logged_in = await server.login_user(user.id)
        async with server.db.user_lock.reader:
            # Sort by tier then sort by id
            achievements = []
            for item in sorted(logged_in.achievements):
                achievements.append(await server.get_achievement_name(item))

        title = user.display_name + f"'s Achievements ({len(achievements)})"
        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(achievements, title, limit)
        paginator = FooterPaginator(embeds)
        await paginator.respond(ctx)

    @bridge.bridge_command()
    @bridge.guild_only()
    async def achievement_progress(
        self, ctx: bridge.Context, user: Optional[User] = None
    ):
        """Shows earned achievements"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if user is None:
            user = ctx.author
        elif user.id not in server.db.users:
            # If user was None, this shouldn't run
            await ctx.respond("🔴 User not found!")
            return

        logged_in = await server.login_user(user.id)
        async with server.db.user_lock.reader:
            # Sort by tier then sort by id
            achievements_progress = []
            highest_tier_achievements = {}
            for achievement in logged_in.achievements:
                if (
                    achievement[0] not in highest_tier_achievements
                    or achievement[1] > highest_tier_achievements[achievement[0]]
                ):
                    highest_tier_achievements[achievement[0]] = achievement[1]
            for item in sorted(
                list(highest_tier_achievements.items())
            ):  # That worked out nice
                achievement_name = await server.get_achievement_name(
                    [item[0], item[1] + 1]
                )
                achievement_progress = await server.get_achievement_progress(
                    item, logged_in
                )
                achievement_counting = await server.get_achievement_item_name(
                    item, achievement_progress
                )
                achievements_progress.append(
                    f"**{achievement_name}**\nYou are {achievement_progress} {achievement_counting} from gaining this achievement\n"
                )

        title = user.display_name + f"'s Achievement progress"
        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(achievements_progress, title, limit)
        paginator = FooterPaginator(embeds)
        await paginator.respond(ctx)

    @bridge.bridge_command()
    @bridge.guild_only()
    async def list_icons(self, ctx: bridge.Context, user: Optional[User] = None):
        """Shows all available icons"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if user is None:
            user = ctx.author
        elif user.id not in server.db.users:
            # If user was None, this shouldn't run
            await ctx.respond("🔴 User not found!")
            return

        logged_in = await server.login_user(user.id)
        icons = []
        async with server.db.user_lock.reader:
            spacing = "\xa0" * 8  # NBSP
            for icon in sorted(
                await server.get_available_icons(logged_in),
                key=lambda icon: server.get_icon_requirement(icon) or [-100, 0],
            ):
                emoji = server.get_icon(icon)
                achievement = server.get_icon_requirement(icon)
                achievement_name = await server.get_achievement_name(achievement)
                icons.append(f"{emoji}{spacing}({achievement_name})")

        title = user.display_name + f"'s Icons ({len(icons)})"
        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(icons, title, limit)
        paginator = FooterPaginator(embeds)
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
        achievements = 0
        for user in server.db.users.values():
            found += len(user.inv)
            cast += user.votes_cast_count
            achievements += len(user.achievements)

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
                EmbedField("🏆 Achievements Earned", f"{achievements:,}", True),
                EmbedField("❌ Polls Rejected", "N/A", True),
            ],
        )
        await ctx.respond(embed=embed)


def setup(client):
    client.add_cog(Lists(client))
