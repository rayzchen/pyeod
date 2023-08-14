from discord.ext import commands, bridge
from pyeod.frontend import (
    DiscordGameInstance,
    InstanceManager,
    ElementalBot,
    FooterPaginator,
    generate_embed_list,
    get_page_limit,
)


class Hint(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    def get_emoji(self, obtainable):
        if obtainable:
            return "<:eodCheck:1139996144093646989>"
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

        user = server.login_user(ctx.author.id)
        lines = []
        for combo in server.db.combo_lookup[element.id]:
            tick = all(elem in user.inv for elem in combo)
            names = [server.db.elem_id_lookup[elem].name for elem in combo]
            names.sort()
            names[-1] = self.obfuscate(names[-1])
            lines.append(self.get_emoji(tick) + " " + " + ".join(names))

        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(
            lines, f"Hints for {element.name} ({len(lines)})", limit
        )
        if element.id in user.inv:
            footer = "You have this"
        else:
            footer = "You don't have this"
        paginator = FooterPaginator(embeds, footer)
        await paginator.respond(ctx)

    @bridge.bridge_command(aliases=["p", "invhint", "ih"])
    async def products(self, ctx: bridge.BridgeContext, *, element: str):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        element = server.check_element(element)

        user = server.login_user(ctx.author.id)
        lines = []
        for combo in server.db.used_in_lookup[element.id]:
            result = server.db.combos[combo]
            tick = result.id in user.inv
            lines.append(self.get_emoji(tick) + " " + result.name)

        unobtained_lines = []
        for line in lines:
            if line.startswith(self.get_emoji(False)):
                unobtained_lines.append(line)
        # Move to end
        for line in unobtained_lines:
            lines.remove(line)
            lines.append(line)

        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(
            lines, f"Products of {element.name} ({len(lines)})", limit
        )
        if element.id in user.inv:
            footer = "You have this"
        else:
            footer = "You don't have this"
        paginator = FooterPaginator(embeds, footer)
        await paginator.respond(ctx)


def setup(client):
    client.add_cog(Hint(client))
