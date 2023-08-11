from discord.ext import commands, bridge, pages
from discord import User, Embed, ButtonStyle
from discord.ext.pages.pagination import Page, PageGroup, PaginatorButton
from pyeod.frontend import DiscordGameInstance, InstanceManager
import math


class FooterPaginator(pages.Paginator):
    def __init__(self, page_list) -> None:
        buttons = [
            pages.PaginatorButton("prev", "◀", style=ButtonStyle.blurple),
            pages.PaginatorButton("next", "▶", style=ButtonStyle.blurple),
        ]
        super(FooterPaginator, self).__init__(
            page_list,
            show_indicator=False,
            author_check=False,
            use_default_buttons=False,
            loop_pages=True,
            custom_buttons=buttons,
        )

    def update_buttons(self):
        buttons = super(FooterPaginator, self).update_buttons()
        page = self.pages[self.current_page]
        if isinstance(page, Embed):
            page.set_footer(text=f"Page {self.current_page + 1}/{self.page_count + 1}")
        return buttons


class Lists(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @bridge.bridge_command()
    async def inv(self, ctx: bridge.BridgeContext, *, user: User = None):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        if user is None:
            user = ctx.author
        elif user.id not in server.db.users:
            # If user was None, this shouldn't run
            await ctx.respond("User not found!")
            return

        logged_in = server.login_user(user.id)
        elements = [server.db.elem_id_lookup[elem].name for elem in logged_in.inv]
        embeds = []
        for i in range(math.ceil(len(elements) / 30)):
            embeds.append(
                Embed(
                    title=user.display_name + "'s Inventory",
                    description="\n".join(elements[i * 30 : i * 30 + 30]),
                )
            )

        paginator = FooterPaginator(embeds)
        await paginator.respond(ctx)


def setup(client):
    client.add_cog(Lists(client))
