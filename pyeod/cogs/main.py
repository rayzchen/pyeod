from discord.ext import commands, tasks, bridge
from discord import default_permissions, DiscordException
from discord.commands import ApplicationContext
from pyeod.utils import format_traceback
from pyeod.frontend import DiscordGameInstance, InstanceManager, ElementalBot
from pyeod.model import GameError
from pyeod import config
import subprocess
import traceback
import sys
import os
import io


class Main(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is ready")
        print("Logged in as:", self.bot.user)
        print("ID:", self.bot.user.id)
        self.restart_checker.start()

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, err: commands.errors.CommandError
    ):
        # Handle different exceptions from parsing arguments here
        if isinstance(err, commands.errors.BadArgument):
            await ctx.reply(str(err))
            return

        if err.__cause__ is not None:
            err = err.__cause__
        if isinstance(err, GameError):
            if err.type == "Not an element":
                await ctx.reply(f"Element **{err.meta['name']}** doesn't exist!")
                return

        lines = traceback.format_exception(type(err), err, err.__traceback__)
        sys.stderr.write("".join(lines))
        error = format_traceback(err)
        await ctx.reply("There was an error processing the command:\n" + error)

    async def on_application_command_error(
        self, ctx: ApplicationContext, err: DiscordException
    ) -> None:
        await self.on_command_error(ctx, err)

    @bridge.bridge_command(aliases=["ms"])
    async def ping(self, ctx: bridge.BridgeContext):
        await ctx.respond(f"Pong {round(self.bot.latency*1000)}ms")

    @bridge.bridge_command()
    @default_permissions(manage_messages=True)
    async def clear_polls(self, ctx: bridge.BridgeContext):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        if server.channels.voting_channel is not None:
            channel = await self.bot.fetch_channel(server.channels.voting_channel)
            for msg_id in server.poll_msg_lookup:
                message = await channel.fetch_message(msg_id)
                await message.delete()
        server.db.polls.clear()
        for user in server.db.users.values():
            user.active_polls = 0
        # TODO: delete polls and notify in news
        await ctx.reply("Cleared polls!")

    @bridge.bridge_command()
    @default_permissions(manage_messages=True)
    async def update(self, ctx: bridge.BridgeContext, revision: str = ""):
        msg = await ctx.respond("Updating...")
        p = subprocess.Popen(["git", "pull"], stderr=subprocess.PIPE)
        _, stderr = p.communicate()
        if p.returncode != 0:
            await msg.edit(f"Command `git pull` exited with code {p.returncode}:\n```{stderr.decode()}```")
            return

        if revision:
            p = subprocess.Popen(["git", "reset", "--hard", revision], stderr=subprocess.PIPE)
            _, stderr = p.communicate()
            if p.returncode != 0:
                await msg.edit(f"Command `git pull` exited with code {p.returncode}:\n```{stderr.decode()}```")
                return

        p = subprocess.Popen(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            await msg.edit(f"Command `git rev-parse HEAD` exited with code {p.returncode}:\n```{stderr.decode()}```")
            return
        await msg.edit(f"Updated successfully to commit {stdout.decode()[:7]}. Restarting")
        open(config.restartfile, "w+").close()

    @tasks.loop(seconds=2)
    async def restart_checker(self):
        if os.path.isfile(config.stopfile):
            print("Stopping")
            # Let main detect stopfile
            self.restart_checker.stop()
            await self.bot.close()
        elif os.path.isfile(config.restartfile):
            os.remove(config.restartfile)
            print("Restarting")
            self.restart_checker.stop()
            await self.bot.close()


def setup(client):
    client.add_cog(Main(client))
