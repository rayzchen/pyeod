__all__ = [
    "FooterPaginator",
    "ElementalBot",
    "autocomplete_elements",
    "autocomplete_categories",
    "LeaderboardPaginator",
    "create_leaderboard",
    "ElementPaginator",
    "create_element_leaderboard",
    "ElementLeaderboardPaginator",
]

from pyeod.frontend.utils import get_page_limit, generate_embed_list
from pyeod.model import Poll, User
from pyeod.errors import InternalError, GameError
from pyeod.frontend.model import DiscordGameInstance, InstanceManager
from pyeod.utils import format_list, calculate_difficulty, obtain_emoji
from discord import (
    ButtonStyle,
    Embed,
    Message,
    AutocompleteContext,
    ui,
    Interaction,
    SelectOption,
)
from discord.ext import bridge, pages
import random


class FooterPaginator(pages.Paginator):
    def __init__(self, page_list, footer_text: str = "", loop: bool = True) -> None:
        buttons = [
            pages.PaginatorButton(
                "prev",
                emoji="<:leftarrow:1182293710684295178>",
                style=ButtonStyle.blurple,
            ),
            pages.PaginatorButton(
                "next",
                emoji="<:rightarrow:1182293601540132945>",
                style=ButtonStyle.blurple,
            ),
        ]
        super(FooterPaginator, self).__init__(
            page_list,
            show_indicator=False,
            author_check=False,
            use_default_buttons=False,
            loop_pages=loop,
            custom_buttons=buttons,
        )
        self.footer_text = footer_text

    def update_buttons(self):
        buttons = super(FooterPaginator, self).update_buttons()
        page = self.pages[self.current_page]
        if isinstance(page, Embed):
            footer = f"Page {self.current_page + 1}/{self.page_count + 1}"
            if self.footer_text:
                footer += " • " + self.footer_text
            # elif page.footer is not None and not page.footer.text.startswith("Page "):
            #     self.footer_text = page.footer.text
            #     footer += " • " + page.footer.text
            page.set_footer(text=footer)
        return buttons


async def create_leaderboard(sorting_option, ctx, user):
    server = InstanceManager.current.get_or_create(ctx.guild.id)
    # Don't add new user to db
    if user.id in server.db.users:
        logged_in = await server.login_user(user.id)
    else:
        logged_in = None

    # Handle the interaction here
    async with server.db.user_lock.reader:
        lines = []
        user_index = -1
        user_inv = 0
        i = 0
        find_value = None
        title = "Top " + sorting_option
        if sorting_option == "Elements Made":
            find_value = lambda user: len(user.inv)
        elif sorting_option == "Elements Suggested":
            find_value = lambda user: len(server.db.created_by_lookup[user.id])
        elif sorting_option == "Combos Suggested":
            find_value = lambda user: user.created_combo_count
        elif sorting_option == "Votes Cast":
            find_value = lambda user: user.votes_cast_count
        elif sorting_option == "Achievements Earned":
            find_value = lambda user: len(user.achievements)
        # TODO - Check how inefficient these are is and make better if it's bad
        elif sorting_option == "Elements Marked":
            markers = [i.marker for i in server.db.elem_id_lookup.values() if i.marker]
            find_value = lambda user: markers.count(user)
        elif sorting_option == "Elements Imaged":
            imagers = [i.imager for i in server.db.elem_id_lookup.values() if i.imager]
            find_value = lambda user: imagers.count(user)
        elif sorting_option == "Elements Colored":
            colorers = [
                i.colorer for i in server.db.elem_id_lookup.values() if i.colorer
            ]
            find_value = lambda user: colorers.count(user)
        elif sorting_option == "Elements Iconed":
            iconers = [i.iconer for i in server.db.elem_id_lookup.values() if i.iconer]
            find_value = lambda user: iconers.count(user)
        else:
            raise GameError("Invalid sort", "Failed to find sort function")

        for user_id, user in sorted(
            server.db.users.items(),
            key=lambda pair: find_value(pair[1]),
            reverse=True,
        ):
            i += 1
            player_value = find_value(user)
            if logged_in is not None and user_id == logged_in.id:
                user_index = i
                user_inv = player_value
                lines.append(
                    f"{i}\. {server.get_icon(user.icon)} <@{user_id}> *You* - {player_value:,}"
                )
            else:
                lines.append(
                    f"{i}\. {server.get_icon(user.icon)} <@{user_id}> - {player_value:,}"
                )

    limit = get_page_limit(server, ctx.channel.id)
    pages = generate_embed_list(lines, title, limit)
    for page in pages:
        page.add_field(name=f"\nYou are #{user_index} on this leaderboard", value="")
    if logged_in is not None and user_id == logged_in.id:
        for page in pages:
            if f"<@{user_id}>" not in page.description:
                page.description += (
                    f"\n\n{user_index}\. <@{user_id} *You* - {user_inv:,}"
                )
    return pages


class SortingDropdown(ui.Select):
    def __init__(self):
        self.sorting_option = "Elements Made"
        options = [
            SelectOption(
                label="Elements Made",
                description="Sorts by elements in inventory",
                emoji="\U0001F392",  # Black freaks out here if the actual char is used
            ),
            SelectOption(
                label="Elements Suggested",
                description="Sorts by new suggested elements",
                emoji="🪄",
            ),
            SelectOption(
                label="Combos Suggested",
                description="Sorts by combos that have been suggested and passed",
                emoji="✍️",
            ),
            SelectOption(
                label="Votes Cast",
                description="Sorts by times voted",
                emoji="🗳️",
            ),
            SelectOption(
                label="Achievements Earned",
                description="Sorts by achievements earned",
                emoji="🌟",
            ),
            SelectOption(
                label="Elements Marked",
                description="Sorts by elements marked",
                emoji="🗣️",
            ),
            SelectOption(
                label="Elements Imaged",
                description="Sorts by elements imaged",
                emoji="🖼️",
            ),
            SelectOption(
                label="Elements Colored",
                description="Sorts by elements colored",
                emoji="🎨",
            ),
            SelectOption(
                label="Elements Iconed",
                description="Sorts by elements iconed",
                emoji="📍",
            ),
            # Add more options as needed
        ]
        super().__init__(
            placeholder="Choose a sorting option...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: Interaction):
        ctx = self.paginator.ctx
        user = self.paginator.target_user

        pages = await create_leaderboard(self.values[0], ctx, user)

        self.paginator.pages = pages
        self.paginator.current_page = 0

        await self.paginator.goto_page(
            self.paginator.current_page, interaction=interaction
        )


class LeaderboardPaginator(FooterPaginator):
    def __init__(
        self, page_list, ctx, user, footer_text: str = "", loop: bool = True
    ) -> None:
        super(LeaderboardPaginator, self).__init__(page_list, footer_text, loop)
        self.show_menu = True
        self.ctx = ctx
        self.target_user = user

    def add_menu(self):
        self.menu = SortingDropdown()
        self.menu.paginator = self
        self.add_item(self.menu)


class ElementListMenu(ui.Select):
    def __init__(self):
        self.sorting_option = "Found"
        options = [
            SelectOption(
                label="Found",
                description="Sorts by the order the elements were found",
                emoji="\U0001F392",  # Black freaks out here if the actual char is used
            ),
            SelectOption(
                label="Created",
                description="Sorts by when the element was created",
                emoji="🪄",
            ),
            SelectOption(
                label="Alphabetical",
                description="Sorts by alphabetical order",
                emoji="🔠",
            ),
            SelectOption(
                label="ID",
                description="Sorts by ID",
                emoji="#️⃣",
            ),
            SelectOption(
                label="Time Created",
                description="Sorts by time the element was created",
                emoji="📅",
            ),
            SelectOption(
                label="Tier",
                description="Sorts by tier",
                emoji="📶",
            ),
            SelectOption(
                label="Tree Size",
                description="Sorts by tree size",
                emoji="🌲",
            ),
            SelectOption(
                label="Creator",
                description="Sorts by who created the element",
                emoji="✍",
            ),
            SelectOption(
                label="Random",
                description="Randomly orders all elements",
                emoji="🎲",
            ),
            SelectOption(
                label="Length",
                description="Sorts by element name length",
                emoji="\u2194",
            ),
            # Add more options as needed
        ]
        super().__init__(
            placeholder="Choose a sorting option...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: Interaction):
        self.sorting_option = self.values[0]
        await self.paginator.regenerate(interaction)


class ElementPaginator(FooterPaginator):
    def __init__(
        self, page_list, initial_sorting, ctx, user, elements, title: str, check: bool, footer_text: str = "", loop: bool = True
    ) -> None:
        super(ElementPaginator, self).__init__(page_list, footer_text, loop)
        self.initial_sorting = initial_sorting
        self.show_menu = True
        self.ctx = ctx
        self.target_user = user
        self.elements = elements
        self.title = title
        self.check = check

    def add_menu(self):
        self.menu = ElementListMenu()
        self.menu.paginator = self
        if not self.footer_text:
            self.footer_text = "Sorting by " + self.initial_sorting
        self.add_item(self.menu)

    async def regenerate(self, interaction):
        pages = await ElementPaginator.generate_pages(
            self.menu.sorting_option,
            self.ctx,
            self.target_user,
            self.elements,
            self.title,
            self.check
        )

        self.current_page = 0
        self.footer_text = "Sorting by " + self.menu.sorting_option

        await self.update(
            pages=pages,
            interaction=interaction,
            show_indicator=False,
            author_check=False,
            use_default_buttons=False,
            loop_pages=self.loop_pages,
            custom_buttons=self.custom_buttons,
        )

    @staticmethod
    async def generate_pages(sorting_option, ctx, user, elements, title, check):
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        logged_in = await server.login_user(user.id)
        async with server.db.element_lock.reader:
            if sorting_option == "Found":
                elements = [elem.name for elem in elements]
            elif sorting_option == "Alphabetical":
                elements = sorted([elem.name for elem in elements])
            elif sorting_option == "Created":
                elements = [
                    elem.name for elem in elements
                    if elem.author is not None and elem.author.id == user.id
                ]
            elif sorting_option == "ID":
                elements = [elem.name for elem in sorted(elements, key=lambda elem: elem.id)]
            elif sorting_option == "Tree Size":
                elements = [
                    elem.name for elem in sorted(
                        elements,
                        key=lambda elem: len(server.db.path_lookup[elem.id]),
                        reverse=True,
                    )
                ]
            elif sorting_option == "Tier":
                elements = [
                    elem.name for elem in sorted(
                        elements,
                        key=lambda elem: server.db.complexities[elem.id],
                        reverse=True,
                    )
                ]
            elif sorting_option == "Time Created":
                elements = [
                    elem.name for elem in sorted(
                        elements,
                        key=lambda elem: elem.created,
                    )
                ]
            elif sorting_option == "Creator":
                elements = [
                    elem.name for elem in sorted(
                        elements,
                        key=lambda elem: elem.author.id if elem.author else 0,
                    )
                ]
            elif sorting_option == "Random":
                elements = [elem.name for elem in elements]
                random.shuffle(elements)
            elif sorting_option == "Length":
                elements = sorted(
                    [elem.name for elem in elements],
                    key=lambda x: len(x)
                )

            if check:
                for i in range(len(elements)):
                    elem = elements[i]
                    found = server.db.elements[elem.lower()].id in logged_in.inv
                    elements[i] = elem + " " + obtain_emoji(found)

        limit = get_page_limit(server, ctx.channel.id)
        return generate_embed_list(
            elements,
            title,
            limit,
            footer="Sorting by " + sorting_option
        )

    @staticmethod
    async def create(*args, footer_text: str = "", loop: bool = True):
        pages = await ElementPaginator.generate_pages(*args)
        paginator = ElementPaginator(pages, *args, footer_text, loop)
        return paginator


async def create_element_leaderboard(sorting_option, ctx, user):
    server = InstanceManager.current.get_or_create(ctx.guild.id)
    # Don't add new user to db
    if user.id in server.db.users:
        logged_in = await server.login_user(user.id)
    else:
        logged_in = None

    # Handle the interaction here
    async with server.db.user_lock.reader:
        lines = []
        i = 0
        find_value = None
        title = "Highest " + sorting_option
        if sorting_option == "Tier":
            find_value = lambda element: server.db.complexities[element.id]
        elif sorting_option == "Tree Size":
            find_value = lambda element: len(server.db.path_lookup[element.id])
        elif sorting_option == "Difficulty":
            find_value = lambda element: calculate_difficulty(
                len(server.db.path_lookup[element.id]),
                server.db.complexities[element.id],
            )
        elif sorting_option == "Made With":
            find_value = lambda element: len(server.db.combo_lookup[element.id])
            title = "Most Combos"
        elif sorting_option == "Used In":
            find_value = lambda element: len(server.db.used_in_lookup[element.id])
            title = "Most Used"
        elif sorting_option == "Found By":
            find_value = lambda element: len(server.db.found_by_lookup[element.id])
            title = "Most Found"
        else:
            raise GameError("Invalid sort", "Failed to find sort function")

        for element_name, element in sorted(
            server.db.elements.items(),
            key=lambda pair: find_value(pair[1]),
            reverse=True,
        ):
            i += 1
            element_value = find_value(element)
            if logged_in is not None and element.id in logged_in.inv:
                if sorting_option != "Difficulty":
                    lines.append(
                        f"{i}\. 📫 **{element.name}** - {element_value:,} *You have this*"
                    )
                else:
                    lines.append(
                        f"{i}\. 📫 **{element.name}** - {element_value:,.2f} *You have this*"
                    )
            else:
                if sorting_option != "Difficulty":
                    lines.append(f"{i}\. 📭 **{element.name}** - {element_value:,}")
                else:
                    lines.append(f"{i}\. 📭 **{element.name}** - {element_value:,.2f}")

    limit = get_page_limit(server, ctx.channel.id)
    pages = generate_embed_list(lines, title, limit)
    return pages


class ElementLeaderboardSortingDropdown(ui.Select):
    def __init__(self):
        self.sorting_option = "Elements Made"
        options = [
            SelectOption(
                label="Difficulty",
                description="Sorts by difficulty",
                emoji="📛",
            ),
            SelectOption(
                label="Tier",
                description="Sorts by tier",
                emoji="📶",
            ),
            SelectOption(
                label="Tree Size",
                description="Sorts by tree size",
                emoji="🌲",
            ),
            SelectOption(
                label="Made With",
                description="Sorts by number of combos for an element",
                emoji="🔨",
            ),
            SelectOption(
                label="Used In",
                description="Sorts by number of combos an element is used in",
                emoji="🧰",
            ),
            SelectOption(
                label="Found By",
                description="Sorts by number of users an element has been found by",
                emoji="🔍",
            ),
            # Add more options as needed
        ]
        super().__init__(
            placeholder="Choose a sorting option...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: Interaction):
        ctx = self.paginator.ctx
        user = self.paginator.target_user

        pages = await create_element_leaderboard(self.values[0], ctx, user)

        self.paginator.pages = pages
        self.paginator.current_page = 0

        await self.paginator.goto_page(
            self.paginator.current_page, interaction=interaction
        )


class ElementLeaderboardPaginator(FooterPaginator):
    def __init__(
        self, page_list, ctx, user, footer_text: str = "", loop: bool = True
    ) -> None:
        super(ElementLeaderboardPaginator, self).__init__(page_list, footer_text, loop)
        self.show_menu = True
        self.ctx = ctx
        self.target_user = user

    def add_menu(self):
        self.menu = ElementLeaderboardSortingDropdown()
        self.menu.paginator = self
        self.add_item(self.menu)


class ElementalBot(bridge.AutoShardedBot):
    async def add_poll(
        self,
        server: DiscordGameInstance,
        poll: Poll,
        msg: Message,
        suggestion_message: str,
    ):
        if server.vote_req == 0:
            await server.check_single_poll(poll)
            if server.channels.news_channel is None:
                raise InternalError(
                    "News channel unset",
                    "Please set the news channel before adding polls",
                )
            news_channel = await self.fetch_channel(server.channels.news_channel)
            news_message = await poll.get_news_message(server)
            if isinstance(news_message, tuple):  # (msg, embed)
                await news_channel.send(news_message[0], embed=news_message[1])
            else:
                await news_channel.send(news_message)
            await news_channel.send(await poll.get_news_message(server))
        else:
            if server.channels.voting_channel is None:
                raise InternalError(
                    "Voting channel unset",
                    "Please set the voting channel before adding polls",
                )
            voting_channel = await self.fetch_channel(server.channels.voting_channel)
            poll_msg = await voting_channel.send(
                embed=await server.convert_poll_to_embed(poll)
            )
            server.poll_msg_lookup[poll_msg.id] = poll
            server.upvoters[poll_msg.id] = set()
            server.downvoters[poll_msg.id] = set()
        await msg.reply(suggestion_message)
        if server.vote_req != 0:  # Adding reactions after just feels snappier
            await poll_msg.add_reaction("\U0001F53C")  # ⬆️ Emoji
            await poll_msg.add_reaction("\U0001F53D")

    async def award_achievements(self, server: DiscordGameInstance, msg: Message = None, user: User = None):
        if msg is not None:
            user = await server.login_user(msg.author.id)
        new_achievements = await server.get_achievements(user)

        unlocked_icons = []

        for achievement in new_achievements:
            if msg is not None:
                await msg.reply(
                    f"🌟 Achievement unlocked: **{await server.get_achievement_name(achievement)}**"
                )
            if server.channels.news_channel is not None:
                news_channel = await self.fetch_channel(server.channels.news_channel)
                await news_channel.send(
                    f"🌟 <@{user.id}> Achievement unlocked: **{await server.get_achievement_name(achievement)}**"
                )
            unlocked_icons += [
                server.get_icon(icon)
                for icon in await server.get_unlocked_icons(achievement)
            ]

        if msg is not None and unlocked_icons:
            if len(unlocked_icons) == 1:
                await msg.reply(f"✨ Icon unlocked: {unlocked_icons[0]}")
            else:
                await msg.reply(
                    f"✨ Icons unlocked: {format_list(unlocked_icons, 'and')}"
                )


async def autocomplete_elements(ctx: AutocompleteContext):
    server = InstanceManager.current.get_or_create(ctx.interaction.guild.id)
    names = []
    async with server.db.element_lock.reader:
        for element in server.db.elements:
            if ctx.value.lower() in element:
                names.append(server.db.elements[element].name)
        return names


async def autocomplete_categories(ctx: AutocompleteContext):
    server = InstanceManager.current.get_or_create(ctx.interaction.guild.id)
    names = []
    async with server.db.category_lock.reader:
        for category in server.db.categories:
            if ctx.value.lower() in category:
                names.append(server.db.categories[category].name)
        return names
