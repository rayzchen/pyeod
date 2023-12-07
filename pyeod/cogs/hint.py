from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    FooterPaginator,
    InstanceManager,
    generate_embed_list,
    get_page_limit,
)
from discord.ext import bridge, commands
import random


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

    @bridge.bridge_command(aliases=["n"])
    @bridge.guild_only()
    async def next(self, ctx: bridge.Context):
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = server.login_user(ctx.author.id)

        sorted_inv = sorted(user.inv)

        for index, i in enumerate(sorted_inv):
            try:
                if i + 1 != sorted_inv[index + 1]:
                    element = server.db.elem_id_lookup[i + 1]
                    break
            except IndexError:
                if i + 1 not in server.db.elem_id_lookup:
                    await ctx.respond("🔴 Could not get next element!")
                    return
                element = server.db.elem_id_lookup[i + 1]
                break

        lines = []
        for combo in server.db.combo_lookup[element.id]:
            tick = all(elem in user.inv for elem in combo)
            names = [server.db.elem_id_lookup[elem].name for elem in combo]
            names.sort()
            names[-1] = self.obfuscate(names[-1])
            lines.append(self.get_emoji(tick) + " " + " + ".join(names))

        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(
            lines, f"Hints for {element.name} ({len(lines)})", limit, element.color
        )
        if element.id in user.inv:
            footer = "📫 You have this"
        else:
            footer = "📭 You don't have this"
        paginator = FooterPaginator(embeds, footer, False)
        await paginator.respond(ctx)

    @bridge.bridge_command(aliases=["h"])
    @bridge.guild_only()
    async def hint(self, ctx: bridge.Context, *, element: str = ""):
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = server.login_user(ctx.author.id)

        if not element:
            inv_set = set(user.inv)
            max_id = max(inv_set)
            choices = set()
            for i in range(1, max_id + 1):
                if i not in inv_set:
                    if i in server.db.elem_id_lookup and i - 1 in inv_set:
                        if all(x in inv_set for x in server.db.combo_lookup[i][0]):
                            choices.add(i)
            if not len(choices):
                for i in range(max_id + 1, max_id + 21):
                    if i in server.db.elem_id_lookup:
                        if all(x in inv_set for x in server.db.combo_lookup[i][0]):
                            choices.add(i)
            if not len(choices):
                # User has every single element
                await ctx.respond("🔴 Could not get any hints!")
                return

            elem = server.db.elem_id_lookup[random.choice(list(choices))]
        else:
            elem = server.check_element(element)

        lines = []
        for combo in server.db.combo_lookup[elem.id]:
            tick = all(elem in user.inv for elem in combo)
            names = [server.db.elem_id_lookup[elem].name for elem in combo]
            names.sort()
            names[-1] = self.obfuscate(names[-1])
            lines.append(self.get_emoji(tick) + " " + " + ".join(names))

        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(
            lines, f"Hints for {elem.name} ({len(lines)})", limit, elem.color
        )
        if elem.id in user.inv:
            footer = "📫 You have this"
        else:
            footer = "📭 You don't have this"
        paginator = FooterPaginator(embeds, footer, False)
        await paginator.respond(ctx)

    @bridge.bridge_command(aliases=["p", "invhint", "ih"])
    @bridge.guild_only()
    async def products(self, ctx: bridge.Context, *, element: str):
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        elem = server.check_element(element)

        user = server.login_user(ctx.author.id)
        lines = []
        for combo in server.db.used_in_lookup[elem.id]:
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
            lines, f"Products of {elem.name} ({len(lines)})", limit, elem.color
        )
        if elem.id in user.inv:
            footer = "📫 You have this"
        else:
            footer = "📭 You don't have this"
        paginator = FooterPaginator(embeds, footer, False)
        await paginator.respond(ctx)


def setup(client):
    client.add_cog(Hint(client))
