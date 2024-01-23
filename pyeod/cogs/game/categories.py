from pyeod import config
from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    ElementPaginator,
    FooterPaginator,
    InstanceManager,
    autocomplete_categories,
    autocomplete_elements,
    generate_embed_list,
    get_page_limit,
    parse_element_list,
)
from pyeod.model import AddCategoryPoll, ElementCategory, RemoveCategoryPoll
from pyeod.utils import format_list
from discord.commands import option as option_decorator
from discord.ext import bridge, commands


class Categories(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @bridge.bridge_command(aliases=["addcat", "ac"])
    @bridge.guild_only()
    @option_decorator("category", autocomplete=autocomplete_categories)
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def add_category(
        self, ctx: bridge.Context, *, category: str, element: str = None
    ):
        """Adds an element to a category"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if not ctx.is_app:
            category, element_list = category.split("|", 1)
            element_list = parse_element_list(element_list)
        else:
            element_list = [element]
        category = category.strip()

        async with server.db.category_lock.reader:
            if category.lower() in server.db.categories:
                category = server.db.categories[category.lower()].name
                if not isinstance(
                    server.db.categories[category.lower()], ElementCategory
                ):
                    await ctx.respond(
                        f"🔴 Cannot add elements to category **{category}**!"
                    )
                    return

        user = await server.login_user(ctx.author.id)
        elements = await server.check_elements(element_list)
        elements = tuple(sorted(elements, key=lambda e: e.id))
        poll = await server.suggest_poll(AddCategoryPoll(user, category, elements))

        if len(elements) == 1:
            element_text = f"**{elements[0].name}**"
        else:
            element_text = f"**{len(elements)}** elements"
        await self.bot.add_poll(
            server,
            poll,
            ctx,
            f"📂 Suggested to add {element_text} to category **{category}**!",
        )

    @bridge.bridge_command(aliases=["rc"])
    @bridge.guild_only()
    @option_decorator("category", autocomplete=autocomplete_categories)
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def remove_category(
        self, ctx: bridge.Context, *, category: str, element: str = None
    ):
        """Removes an element from a category"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if not ctx.is_app:
            category, element_list = category.split("|", 1)
            element_list = parse_element_list(element_list)
        else:
            element_list = [element]
        category = category.strip()

        async with server.db.category_lock.reader:
            if category.lower() in server.db.categories:
                category = server.db.categories[category.lower()].name
                if not isinstance(
                    server.db.categories[category.lower()], ElementCategory
                ):
                    await ctx.respond(
                        f"🔴 Cannot remove elements from category **{category}**!"
                    )
                    return
            else:
                await ctx.respond(f"🔴 Category **{category}** doesn't exist!")
                return

        user = await server.login_user(ctx.author.id)
        elements = await server.check_elements(element_list)
        elements = tuple(sorted(elements, key=lambda e: e.id))
        async with server.db.category_lock.reader:
            if category.lower() in server.db.categories:
                filtered_elements = [
                    e
                    for e in elements
                    if e in server.db.categories[category.lower()].elements
                ]
                if len(filtered_elements) == 0:
                    element_list = format_list([f"**{e.name}**" for e in elements])
                    await ctx.respond(
                        f"🔴 Category **{category}** does not contain **{element_list}**!"
                    )
                    return
                elements = filtered_elements
        poll = await server.suggest_poll(RemoveCategoryPoll(user, category, elements))

        if len(elements) == 1:
            element_text = f"**{elements[0].name}**"
        else:
            element_text = f"**{len(elements)}** elements"
        await self.bot.add_poll(
            server,
            poll,
            ctx,
            f"📂 Suggested to remove {element_text} from category **{category}**!",
        )

    @bridge.bridge_command(aliases=["cat"])
    @bridge.guild_only()
    @option_decorator("category", autocomplete=autocomplete_categories)
    async def category(self, ctx: bridge.Context, category: str = ""):
        """Lists all categories, or lists all elements of a category"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = await server.login_user(ctx.author.id)

        if not category:
            lines = []
            async with server.db.category_lock.reader:
                for name, category in server.db.categories.items():
                    if not isinstance(category, ElementCategory):
                        lines.append(name)
                    else:
                        total = 0
                        for element in category.elements:
                            if element.id in user.inv:
                                total += 1
                        percentage = total / len(category.elements)
                        if percentage == 1:
                            lines.append(f"{name} {obtain_emoji(True)}")
                        else:
                            lines.append(f"{name} ({percentage:.2f}%)")

            limit = get_page_limit(server, ctx.channel.id)
            embeds = generate_embed_list(
                lines,
                f"All Categories ({len(server.db.categories)})",
                limit,
                config.EMBED_COLOR,
            )
            paginator = FooterPaginator(embeds)
            await paginator.respond(ctx)
        else:
            category_name = category.lower()
            if category_name not in server.db.categories:
                await ctx.respond(f"🔴 Category **{category}** doesn't exist!")
                return
            category = server.db.categories[category_name]
            total = 0
            elements = category.get_elements(server.db)
            for element in elements:
                if element.id in user.inv:
                    total += 1
            progress = total / len(elements)
            title = f"{category.name} ({len(elements)}, {progress:.2f}%)"
            paginator = await ElementPaginator.create(
                "Alphabetical", ctx, ctx.author, elements, title, True
            )
            await paginator.respond(ctx)


def setup(client):
    client.add_cog(Categories(client))
