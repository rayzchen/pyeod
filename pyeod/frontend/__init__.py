from pyeod.frontend.model import *
from pyeod.frontend.utils import *
from pyeod.model import Poll, InternalError
from discord.ext import pages, bridge
from discord import ButtonStyle, Embed


class FooterPaginator(pages.Paginator):
    def __init__(self, page_list, footer_text: str = "", loop: bool = True) -> None:
        buttons = [
            pages.PaginatorButton("prev", "◀", style=ButtonStyle.blurple),
            pages.PaginatorButton("next", "▶", style=ButtonStyle.blurple),
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
        ctx: bridge.Context,
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
            msg = await voting_channel.send(embed=server.convert_poll_to_embed(poll))
            server.poll_msg_lookup[msg.id] = poll
        await ctx.respond(suggestion_message)
        if server.vote_req != 0:  # Adding reactions after just feels snappier
            await msg.add_reaction("\U0001F53C")  # ⬆️ Emoji
            await msg.add_reaction("\U0001F53D")
