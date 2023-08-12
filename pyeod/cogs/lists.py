from discord.ext import commands, bridge
from discord import User
from pyeod.frontend import (
    DiscordGameInstance,
    InstanceManager,
    FooterPaginator,
    generate_embed_list,
    get_page_limit
)


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
        title = user.display_name + f"'s Inventory ({len(logged_in.inv)})"

        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(elements, title, limit)
        paginator = FooterPaginator(embeds)
        await paginator.respond(ctx)


def setup(client):
    client.add_cog(Lists(client))
