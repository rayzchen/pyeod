from pyeod.errors import GameError, InternalError
from pyeod.frontend import (
    ElementalBot,
    InstanceManager,
    autocomplete_elements,
    prepare_file,
)
from discord.ext.bridge import bridge_option as option_decorator
from discord.ext import bridge, commands
import io


class Path(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @bridge.bridge_command()
    @bridge.guild_only()
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def path(self, ctx: bridge.BridgeContext, *, element: str) -> None:
        """Gives the step by step element creation towards a certain element.
        Ie. !path mud would `water+earth=mud`"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if server.db.complexity_lock.reader.locked:
            raise InternalError("Complexity lock", "Complexity calculations in process")

        logged_in = await server.login_user(ctx.author.id)
        elem = await server.get_element_by_str(logged_in, element)

        if not ctx.author.guild_permissions.manage_guild:
            if elem.id not in logged_in.inv:
                raise GameError(
                    "Not in inv",
                    f"You don't have {element.name}!",
                    {"element": element, "user": user},
                )

        path = await server.db.get_path(elem)
        async with server.db.element_lock.reader:
            lines = []
            i = 0
            for pathelem in path:
                combo = server.db.min_elem_tree[pathelem]
                if not combo:
                    # Only starter elements should end up here
                    continue
                i += 1
                elements = [server.db.elem_id_lookup[x].name for x in combo]
                result = server.db.elem_id_lookup[pathelem].name
                lines.append(str(i) + ". " + " + ".join(elements) + " = " + result)

        stream = io.StringIO("\n".join(lines))
        user = await self.bot.fetch_user(ctx.author.id)
        await ctx.defer()
        await user.send(
            f"Path for **{elem.name}**:", file=prepare_file(stream, "path.txt")
        )
        await ctx.respond("💬 Sent path in DM!")


def setup(client):
    client.add_cog(Path(client))
