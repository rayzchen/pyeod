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
from pyeod.utils import format_list, obtain_emoji
from discord.ext.bridge import bridge_option as option_decorator
from discord.ext import bridge, commands


class Categories(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @bridge.bridge_command(aliases=["addcat", "ac"])
    @bridge.guild_only()
    @option_decorator("category", autocomplete=autocomplete_categories)
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def add_category(
        self, ctx: bridge.BridgeContext, *, category: str, element: str = None
    ):
        """Adds an element to a category"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if not ctx.is_app:
            category, element_list = category.split("|", 1)
            element_list = parse_element_list(element_list)
        else:
            element_list = [element]

        user = await server.login_user(ctx.author.id)
        element_list = [
            (await server.get_element_by_str(user, i)).name for i in element_list
        ]

        # python>=3.7 only
        element_list = list(dict.fromkeys(element_list))
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
            else:
                if len(category) > 256:
                    await ctx.respond(
                        "🔴 Category names cannot be longer than 256 characters!"
                    )
                    return
                if category.startswith("#"):
                    await ctx.respond("🔴 Category names cannot start with **#**!")
                    return
                if "\n" in category:
                    await ctx.respond("🔴 Category names cannot contain newlines!")
                    return
                if "<@" in category:
                    await ctx.respond("🔴 Category names cannot contain **<@**!")
                    return
                # Allow users to do potential dumb formatting shit, but also allow normal use of these strings
                # Backslash escape all fucked up discord shit
                for bad_string in [
                    "\\",
                    "</",
                    "<#",
                    "_",
                    "|",
                    "```",
                    "*",
                    ">",
                    "<:",
                    "<sound",
                ]:
                    category = category.replace(bad_string, f"\\{bad_string}")
                category = category.replace("\u200C", "")  # ZWNJ

                if len(category) > 256:
                    await ctx.respond(
                        "🔴 Category names cannot be longer than 256 characters!"
                    )
                    return
                if category == "":
                    await ctx.respond("🔴 Please give a valid category name!")
                    return
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
        self, ctx: bridge.BridgeContext, *, category: str, element: str = None
    ):
        """Removes an element from a category"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if not ctx.is_app:
            category, element_list = category.split("|", 1)
            element_list = parse_element_list(element_list)
        else:
            element_list = [element]
        logged_in = await server.login_user(ctx.author.id)
        for i in range(len(element_list)):
            element_list[i] = await server.get_element_by_str(user, element_list[i])

        # python>=3.7 only
        element_list = list(dict.fromkeys(element_list))
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
    async def category(self, ctx: bridge.BridgeContext, *, category: str = ""):
        """Lists all categories, or lists all elements of a category"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = await server.login_user(ctx.author.id)

        if not category:
            lines = []
            async with server.db.category_lock.reader:
                for category in server.db.categories.values():
                    if not isinstance(category, ElementCategory):
                        lines.append(category.name)
                    else:
                        total = 0
                        for element in category.elements:
                            if element.id in user.inv:
                                total += 1
                        percentage = total / len(category.elements) * 100
                        if percentage == 100:
                            lines.append(f"{category.name} {obtain_emoji(True)}")
                        else:
                            lines.append(f"{category.name} ({percentage:.2f}%)")

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
            elements = await category.get_elements(server.db)
            for element in elements:
                if element.id in user.inv:
                    total += 1
            progress = total / len(elements) * 100
            title = f"{category.name} ({len(elements)}, {progress:.2f}%)"
            paginator = await ElementPaginator.create(
                "Alphabetical", ctx, ctx.author, elements, title, True
            )
            await paginator.respond(ctx)


def setup(client):
    client.add_cog(Categories(client))
