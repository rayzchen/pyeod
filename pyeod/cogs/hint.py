from discord.ext import commands, bridge, pages
from discord import User, Embed, ButtonStyle
from discord.ext.pages.pagination import Page, PageGroup, PaginatorButton
from pyeod.frontend import (
    DiscordGameInstance,
    InstanceManager,
    FooterPaginator,
    generate_embed_list,
)
import math


class Hint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_emoji(self, obtainable):
        if obtainable:
            return "✅"
        else:
            return "❌"

    def obfuscate(self, name):
        punctuation = " .*()-!+"
        chars = list(name)
        for i in range(len(chars)):
            if chars[i] not in punctuation:
                chars[i] = "?"
        return "".join(chars)

    @bridge.bridge_command(aliases=["h"])
    async def hint(self, ctx: bridge.BridgeContext, *, element: str = ""):
        if not element:
            await ctx.respond("Not implemented")
            return

        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        element = server.check_element(element)

        # Need better way to get combos
        combo_ids = []
        for combo in server.db.combos:
            if server.db.combos[combo] == element:
                combo_ids.append(combo)

        user = server.login_user(ctx.author.id)
        lines = []
        for combo in combo_ids:
            tick = all(elem in user.inv for elem in combo)
            names = [server.db.elem_id_lookup[elem].name for elem in combo]
            names.sort()
            names[-1] = self.obfuscate(names[-1])
            lines.append(" + ".join(names) + " " + self.get_emoji(tick))

        embeds = generate_embed_list(
            lines, f"Hints for {element.name} ({len(lines)})", 30
        )
        paginator = FooterPaginator(embeds)
        await paginator.respond(ctx)


def setup(client):
    client.add_cog(Hint(client))
