__all__ = [
    "FooterPaginator",
    "ElementalBot",
    "autocomplete_elements",
    "LeaderboardPaginator",
    "create_leaderboard",
]

from .utils import get_page_limit, generate_embed_list
from pyeod.model import Poll
from pyeod.errors import InternalError, GameError
from pyeod.frontend.model import DiscordGameInstance, InstanceManager
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
                lines.append(f"{i}\. <@{user_id}> *You* - {player_value:,}")
            else:
                lines.append(f"{i}\. <@{user_id}> - {player_value:,}")

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
                description="Sorts by number of new suggested elements",
                emoji="🪄",
            ),
            SelectOption(
                label="Combos Suggested",
                description="Sorts by combos that have been suggested and passed",
                emoji="✍️",
            ),
            SelectOption(
                label="Votes Cast",
                description="Sorts by amount of times voted",
                emoji="🗳️",
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
        user = self.paginator.user

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
        self.user = user

    def add_menu(self):
        self.menu = SortingDropdown()
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
        await msg.reply(suggestion_message)
        if server.vote_req != 0:  # Adding reactions after just feels snappier
            await poll_msg.add_reaction("\U0001F53C")  # ⬆️ Emoji
            await poll_msg.add_reaction("\U0001F53D")


async def autocomplete_elements(ctx: AutocompleteContext):
    server = InstanceManager.current.get_or_create(ctx.interaction.guild.id)
    names = []
    async with server.db.element_lock.reader:
        for element in server.db.elements:
            if ctx.value.lower() in element:
                names.append(server.db.elements[element].name)
        return names
