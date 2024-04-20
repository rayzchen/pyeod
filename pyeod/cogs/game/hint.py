from pyeod.errors import GameError
from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    FooterPaginator,
    InstanceManager,
    autocomplete_elements,
    generate_embed_list,
    get_page_limit,
)
from pyeod.utils import obtain_emoji
from discord.commands import option as option_decorator
from discord.ext import bridge, commands
from typing import Optional
import random


class Hint(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    def obfuscate(self, name):
        punctuation = " .*()-!+"
        chars = list(name)
        for i in range(len(chars)):
            if chars[i] not in punctuation:
                chars[i] = "?"
        return "".join(chars)

    @bridge.bridge_command(aliases=["n"])
    @bridge.guild_only()
    async def next(self, ctx: bridge.BridgeExtContext):
        """Gives a hint for the lowest element id you are missing"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = await server.login_user(ctx.author.id)

        async with server.db.element_lock.reader:
            sorted_inv = sorted(user.inv)
            last_element = sorted_inv[0]
            for i in range(1, len(sorted_inv)):
                found = False
                for j in range(last_element + 1, sorted_inv[i]):
                    if j in server.db.elem_id_lookup:
                        last_element = j - 1
                        found = True
                        break
                if found:
                    break
                last_element = sorted_inv[i]
            else:
                # User has all elements
                if last_element + 1 not in server.db.elem_id_lookup:
                    raise GameError("No more elements", "You have all the elements!")
            element = server.db.elem_id_lookup[last_element + 1]

            lines = []
            for combo in server.db.combo_lookup[element.id]:
                tick = all(elem in user.inv for elem in combo)
                names = [server.db.elem_id_lookup[elem].name for elem in combo]
                names.sort()
                names[-1] = self.obfuscate(names[-1])
                lines.append(obtain_emoji(tick) + " " + " + ".join(names))

        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(
            lines,
            f"Hints for {element.name} ({len(lines)})",
            limit,
            element.color,
            element.image,
        )
        if element.id in user.inv:
            footer = "📫 You have this"
        else:
            footer = "📭 You don't have this"
        paginator = FooterPaginator(embeds, footer, False)
        await paginator.respond(ctx)

    @bridge.bridge_command(aliases=["h"])
    @bridge.guild_only()
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def hint(self, ctx: bridge.BridgeExtContext, *, element: str = ""):
        """Gives a random or specified hint for how to make an element"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = await server.login_user(ctx.author.id)

        async with server.db.element_lock.reader:
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
                    raise GameError("No more elements", "You have all the elements!")

                elem = server.db.elem_id_lookup[random.choice(list(choices))]
            else:
                elem = await server.get_element_by_str(user, element)

            lines = []
            for combo in server.db.combo_lookup[elem.id]:
                tick = all(elem in user.inv for elem in combo)
                names = [server.db.elem_id_lookup[elem].name for elem in combo]
                names.sort()
                names[-1] = self.obfuscate(names[-1])
                lines.append(obtain_emoji(tick) + " " + " + ".join(names))

        limit = get_page_limit(server, ctx.channel.id)
        embeds = generate_embed_list(
            lines,
            f"Hints for {elem.name} ({len(lines)})",
            limit,
            elem.color,
            elem.image,
        )
        if elem.id in user.inv:
            footer = "📫 You have this"
        else:
            footer = "📭 You don't have this"
        paginator = FooterPaginator(embeds, footer)
        await paginator.respond(ctx)

    @bridge.bridge_command(aliases=["p", "invhint", "ih"])
    @bridge.guild_only()
    @option_decorator("element", str, autocomplete=autocomplete_elements)
    async def products(self, ctx: bridge.BridgeExtContext, *, element: Optional[str] = ""):
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        user = await server.login_user(ctx.author.id)

        elem = await server.get_element_by_str(user, element)

        async with server.db.element_lock.reader:
            lines = []
            sorter = lambda combo: server.db.combos[combo].id
            for combo in sorted(server.db.used_in_lookup[elem.id], key=sorter):
                result = server.db.combos[combo]
                tick = result.id in user.inv
                line = obtain_emoji(tick) + " " + result.name
                if line not in lines:
                    # In case multiple combos use this element for the same result
                    lines.append(obtain_emoji(tick) + " " + result.name)

        unobtained_emoji = obtain_emoji(False)
        unobtained_lines = []
        for line in lines:
            if line.startswith(unobtained_emoji):
                unobtained_lines.append(line)
        # Move to end preserving order
        for line in unobtained_lines:
            lines.remove(line)
            lines.append(line)

        limit = get_page_limit(server, ctx.channel.id)
        title = f"Products of {elem.name} ({len(lines)})"
        embeds = generate_embed_list(lines, title, limit, elem.color)
        if elem.id in user.inv:
            footer = "📫 You have this"
        else:
            footer = "📭 You don't have this"
        paginator = FooterPaginator(embeds, footer)
        await paginator.respond(ctx)


def setup(client):
    client.add_cog(Hint(client))
