__all__ = ["FooterPaginator", "ElementalBot"]

from pyeod.frontend.model import __all__ as _model_all
from pyeod.frontend.utils import __all__ as _utils_all

__all__.extend(_model_all)
__all__.extend(_utils_all)

from pyeod.frontend.model import *
from pyeod.frontend.utils import *
from pyeod.errors import InternalError
from pyeod.model import Poll
from discord import ButtonStyle, Embed, Emoji, Message
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


class ElementalBot(bridge.AutoShardedBot):
    async def add_poll(
        self,
        server: DiscordGameInstance,
        poll: Poll,
        msg: Message,
        suggestion_message: str,
    ):
        if server.vote_req == 0:
            server.check_single_poll(poll)
            if server.channels.news_channel is None:
                raise InternalError(
                    "News channel unset",
                    "Please set the news channel before adding polls",
                )
            news_channel = await self.fetch_channel(server.channels.news_channel)
            await news_channel.send(poll.get_news_message(server))
        else:
            if server.channels.voting_channel is None:
                raise InternalError(
                    "Voting channel unset",
                    "Please set the voting channel before adding polls",
                )
            voting_channel = await self.fetch_channel(server.channels.voting_channel)
            poll_msg = await voting_channel.send(
                embed=server.convert_poll_to_embed(poll)
            )
            server.poll_msg_lookup[poll_msg.id] = poll
        await msg.reply(suggestion_message)
        if server.vote_req != 0:  # Adding reactions after just feels snappier
            await poll_msg.add_reaction("\U0001F53C")  # ⬆️ Emoji
            await poll_msg.add_reaction("\U0001F53D")
