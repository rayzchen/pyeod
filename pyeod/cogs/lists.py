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
from discord.ext.bridge import bridge_option as option_decorator
from discord.ext import bridge, commands
from typing import Optional


class Lists(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @bridge.bridge_command()
    @bridge.guild_only()
    async def inv(self, ctx: bridge.BridgeContext, user: Optional[User] = None):
        """Shows your elements"""

        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if user is None:
            user = ctx.author
        elif user.id not in server.db.users:
            raise GameError("No user", "User not found!")

        logged_in = await server.login_user(user.id)
        inv = [server.db.elem_id_lookup[e] for e in logged_in.inv]
        title = user.display_name + f"'s Inventory ({len(inv)})"
        paginator = await ElementPaginator.create("Found", ctx, user, inv, title, False)
        await paginator.respond(ctx)

    @bridge.bridge_command()
    @bridge.guild_only()
    async def achievements(self, ctx: bridge.BridgeContext, user: Optional[User] = None):
        """Shows earned achievements"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if user is None:
            user = ctx.author
        elif user.id not in server.db.users:
            # If user was None, this shouldn't run
            raise GameError("No user", "User not found!")

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
        self, ctx: bridge.BridgeContext, user: Optional[User] = None
    ):
        """Shows earned achievements"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if user is None:
            user = ctx.author
        elif user.id not in server.db.users:
            # If user was None, this shouldn't run
            raise GameError("No user", "User not found!")

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
            for item in sorted(highest_tier_achievements.items()):
                achievement_name = await server.get_achievement_name(
                    [item[0], item[1] + 1]
                )
                achievement_progress = await server.get_achievement_progress(
                    item, logged_in
                )
                match item[0]:
                    case 11:
                        progress_string = (
                            f"(your highest: {achievement_progress[1]:,.2f})"
                        )
                        achievement_counting = await server.get_achievement_item_name(
                            item
                        )
                        achievements_progress.append(
                            f"**{achievement_name}**\n{progress_string} You need an element with a {achievement_counting} of {achievement_progress[0]}\n"
                        )
                    case 9 | 10:  # Catch the tree size, tier, and difficulty achievements
                        progress_string = f"(your highest: {achievement_progress[1]:,})"
                        achievement_counting = await server.get_achievement_item_name(
                            item
                        )
                        achievements_progress.append(
                            f"**{achievement_name}**\n{progress_string} You need an element with a {achievement_counting} of {achievement_progress[0]}\n"
                        )
                    case 3:  # No leaderboard achievement progress
                        pass
                    case _:
                        progress_string = (
                            f"({achievement_progress[1]:,}/{achievement_progress[0]:,})"
                        )
                        difference = achievement_progress[0] - achievement_progress[1]
                        achievement_counting = await server.get_achievement_item_name(
                            item, difference
                        )
                        if difference < 0:
                            # leaderboard
                            progress_string = f"({achievement_progress[1]})"
                            difference = (
                                achievement_progress[1] - achievement_progress[0]
                            )
                        if achievement_name is not None:
                            achievements_progress.append(
                                f"**{achievement_name}**\n{progress_string} You are {difference} {achievement_counting} away from gaining this achievement\n"
                            )
                        else:
                            achievements_progress.append(
                                f"**{await server.get_achievement_name([item[0], item[1]])}**\nYou have reached the max achievement\n"
                            )

        title = user.display_name + f"'s Achievement progress"
        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(achievements_progress, title, limit)
        paginator = FooterPaginator(embeds)
        await paginator.respond(ctx)

    @bridge.bridge_command()
    @bridge.guild_only()
    async def list_icons(self, ctx: bridge.BridgeContext, user: Optional[User] = None):
        """Shows all available icons"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if user is None:
            user = ctx.author
        elif user.id not in server.db.users:
            # If user was None, this shouldn't run
            raise GameError("No user", "User not found!")

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
    async def stats(self, ctx: bridge.BridgeContext):
        import time

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
                EmbedField("🔄 Combination Count", f"{combinations:,}", True),
                EmbedField("🧑‍🤝‍🧑 User Count", f"{users:,}", True),
                EmbedField("🔍 Elements Found", f"{found:,}", True),
                EmbedField(
                    "📁 Elements Categorized", f"{len(categorized_element_ids):,}", True
                ),
                EmbedField("👨‍💻 Commands Used", f"{server.commands_used:,}", True),
                EmbedField("🗳️ Votes Cast", f"{cast:,}", True),
                EmbedField("🏆 Achievements Earned", f"{achievements:,}", True),
                EmbedField("❌ Polls Rejected", f"{server.polls_rejected:,}", True),
            ],
        )
        await ctx.respond(embed=embed)

    @bridge.bridge_command(aliases=["f"])
    @bridge.guild_only()
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def found(self, ctx: bridge.BridgeContext, *, element):
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = await server.login_user(ctx.author.id)

        elem = await server.get_element_by_str(user, element)
        found = [
            f"<@{user.id}>" for user in server.db.users.values() if elem.id in user.inv
        ]
        title = "Users who have found " + elem.name + f" ({len(found)})"
        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(found, title, limit)

        paginator = FooterPaginator(embeds)
        await paginator.respond(ctx)


def setup(client):
    client.add_cog(Lists(client))
