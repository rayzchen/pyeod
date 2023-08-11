from discord.ext import commands, bridge, pages
from discord import User, Embed, ButtonStyle
from pyeod.frontend import DiscordGameInstance, InstanceManager
import math


class FooterPaginator(pages.Paginator):
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
            logged_in = server.login_user(ctx.author.id)
        elif user.id not in server.db.users:
            await ctx.respond("User not found!")
            return
        else:
            logged_in = server.login_user(user.id)

        elements = [
            server.db.elem_id_lookup[elem].name for elem in logged_in.inv
        ]
        page_list = []
        for i in range(math.ceil(len(elements) / 30)):
            page_list.append(Embed(description="\n".join(elements[i*30:i*30+30])))

        buttons = [
            pages.PaginatorButton("prev", "◀", style=ButtonStyle.blurple),
            pages.PaginatorButton("next", "▶", style=ButtonStyle.blurple)
        ]

        paginator = FooterPaginator(
            page_list,
            show_indicator=False,
            author_check=False,
            use_default_buttons=False,
            loop_pages=True,
            custom_buttons=buttons
        )
        await paginator.respond(ctx)


def setup(client):
    client.add_cog(Lists(client))
