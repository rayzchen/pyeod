from pyeod.errors import InternalError
from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    InstanceManager,
    prepare_file,
    autocomplete_elements
)
from discord.ext import bridge, commands
from discord.commands import option as option_decorator
import io


class Path(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @bridge.bridge_command()
    @bridge.guild_only()
    @option_decorator("element", autocomplete=autocomplete_elements)
    async def path(self, ctx: bridge.Context, *, element: str) -> None:
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if server.db.complexity_lock.reader.locked:
            raise InternalError("Complexity lock", "Complexity calculations in process")
        if element.startswith("#"):
            id_str = element[1:].strip()
            if not id_str.isdecimal():
                await ctx.respond(f"🔴 Element ID **{id_str}** doesn't exist!")
                return
            elem_id = int(id_str)
            async with server.db.element_lock.reader:
                if elem_id not in server.db.elem_id_lookup:
                    await ctx.respond(f"🔴 Element ID **{elem_id}** doesn't exist!")
                    return
                elem = server.db.elem_id_lookup[elem_id]
        else:
            elem = await server.check_element(element)

        if not ctx.author.guild_permissions.manage_guild:
            logged_in = await server.login_user(ctx.author.id)
            if elem.id not in logged_in.inv:
                await ctx.respond(f"🔴 You don't have **{elem.name}**!")
                return

        async with server.db.element_lock.reader:
            lines = []
            i = 0
            for pathelem in await server.db.get_path(elem):
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
