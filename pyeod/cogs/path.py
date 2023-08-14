from discord.ext import commands, tasks, bridge
from discord.utils import get
from discord import Message, TextChannel, File
from pyeod.frontend import InstanceManager, DiscordGameInstance
from typing import Optional
import io


class Path(commands.Cog):
    def __init__(self, bot: bridge.AutoShardedBot):
        self.bot = bot

    @bridge.bridge_command()
    async def path(self, ctx: bridge.Context, element: str):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        if element.startswith("#"):
            elem_id = element[1:].strip()
            if not elem_id.isdecimal():
                await ctx.respond(f"Element ID **{elem_id}** doesn't exist!")
                return
            elem_id = int(elem_id)
            if elem_id not in server.db.elem_id_lookup:
                await ctx.respond(f"Element ID **{elem_id}** doesn't exist!")
                return
            element = server.db.elem_id_lookup[elem_id]
        else:
            element = server.check_element(element)

        logged_in = server.login_user(ctx.author.id)
        # if element.id not in logged_in.inv:
        #     await ctx.respond(f"You don't have **{element.name}**!")
        #     return

        lines = []
        i = 0
        for elem, combo in server.db.paths[element.id].items():
            if combo is None:
                # Only starter elements should end up here
                continue
            i += 1
            elements = [server.db.elem_id_lookup[x].name for x in combo]
            result = server.db.elem_id_lookup[elem].name
            lines.append(
                str(i) + ". " + " + ".join(elements) + " = " + result
            )

        stream = io.StringIO("\n".join(lines))
        user = await self.bot.fetch_user(ctx.author.id)
        await user.send(
            f"Path for **{element.name}**:",
            file=File(fp=stream, filename="path.txt")
        )
        await ctx.respond("Sent path in DM!")


def setup(client):
    client.add_cog(Path(client))
