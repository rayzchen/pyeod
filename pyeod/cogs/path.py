from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    InstanceManager,
    prepare_file,
)
from pyeod.model import InternalError
from discord.ext import bridge, commands
import io


class Path(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @bridge.bridge_command()
    @bridge.guild_only()
    async def path(self, ctx: bridge.Context, element: str) -> None:
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if server.db.complexity_lock:
            raise InternalError("Complexity lock", "Complexity calculations in process")
        if element.startswith("#"):
            id_str = element[1:].strip()
            if not id_str.isdecimal():
                await ctx.respond(f"🔴 Element ID **{id_str}** doesn't exist!")
                return
            elem_id = int(id_str)
            if elem_id not in server.db.elem_id_lookup:
                await ctx.respond(f"🔴 Element ID **{elem_id}** doesn't exist!")
                return
            elem = server.db.elem_id_lookup[elem_id]
        else:
            elem = server.check_element(element)

        logged_in = server.login_user(ctx.author.id)
        if elem.id not in logged_in.inv:
            await ctx.respond(f"🔴 You don't have **{elem.name}**!")
            return
        await ctx.defer()

        lines = []
        i = 0
        for pathelem in server.db.get_path(elem):
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
        await user.send(
            f"Path for **{elem.name}**:", file=prepare_file(stream, "path.txt")
        )
        await ctx.respond("💬 Sent path in DM!")


def setup(client):
    client.add_cog(Path(client))
