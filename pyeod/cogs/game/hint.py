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
import time, random


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

    @bridge.bridge_command(aliases=["h"])
    @bridge.guild_only()
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def hint(self, ctx: bridge.Context, *, element: str = ""):
        time.sleep(random.uniform(0,1.5))
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
                    raise GameError("No more elements", "You have all the elements")

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
            footer = "You have this"
        else:
            footer = "You don't have this"
        paginator = FooterPaginator(embeds, footer)
        await paginator.respond(ctx)


def setup(client):
    client.add_cog(Hint(client))
