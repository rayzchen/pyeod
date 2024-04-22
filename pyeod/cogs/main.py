from pyeod import config
from pyeod.errors import GameError, InternalError
from pyeod.frontend import ElementalBot, InstanceManager
from pyeod.utils import format_list, format_traceback, defer
from discord import ButtonStyle, Embed
from discord.commands import ApplicationContext
from discord.errors import ApplicationCommandInvokeError
from discord.ext import bridge, commands, pages, tasks
import discord
import os
import typing
import inspect
import traceback
import subprocess


class Main(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is ready")
        print("Logged in as:", self.bot.user)
        print("ID:", self.bot.user.id)

        if not self.restart_checker.is_running():
            self.restart_checker.start()
        if not self.achievement_checker.is_running():
            self.achievement_checker.start()

    @commands.Cog.listener()
    async def on_bridge_command(self, ctx: bridge.BridgeContext):
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        server.commands_used += 1

    @commands.Cog.listener()
    async def on_bridge_command_error(
        self, ctx: bridge.BridgeContext, err: commands.errors.CommandError
    ):
        # Handle different exceptions from parsing arguments here
        if isinstance(err, commands.errors.BadArgument):
            await ctx.respond("🔴 " + str(err))
            return

        if isinstance(
            err, (commands.errors.CommandInvokeError, ApplicationCommandInvokeError)
        ):
            err = err.original
        handled = False
        if isinstance(err, GameError):
            if "emoji" not in err.meta:
                await ctx.respond(f"🔴 {err.message}", ephemeral=True)
            else:
                await ctx.respond(f"{err.meta['emoji']} {err.message}", ephemeral=True)
            return
        elif isinstance(err, InternalError):
            if err.type == "Complexity lock":
                await ctx.respond(
                    f"🔴 Complexity calculations ongoing, cannot access element data"
                )
                handled = True
        if handled:
            return

        lines = traceback.format_exception(type(err), err, err.__traceback__)
        error = format_traceback(err)
        await ctx.respond("⚠️ There was an error processing the command:\n" + error)

    # General command error listener
    # Listens to bridge commands even if an on_bridge_command_error listener is already present. For some reason.
    # TODO: listener exception filtering using on_error
    @commands.Cog.listener()
    async def on_command_error(  # Suppress stderr printing on already handled errors
        self, ctx: commands.Context, err: commands.errors.CommandError
    ):
        pass

    @commands.Cog.listener()
    async def on_application_command_error(
        self, ctx: ApplicationContext, err: commands.errors.CommandError
    ):
        pass

    @bridge.bridge_command(aliases=["ms"])
    async def ping(self, ctx: bridge.BridgeContext):
        """Gets the current ping between the bot and discord"""
        await ctx.respond(f"🏓 Pong! {round(self.bot.latency*1000)}ms")

    @bridge.bridge_command()
    async def update(self, ctx: bridge.BridgeContext, *, revision: str = ""):
        """Updates to the latest github commit"""
        if ctx.author.id not in config.SERVER_CONTROL_USERS:
            raise GameError("No permission", "You don't have permission to do that!")
        if ctx.is_app:
            msg = await ctx.respond("💽 Updating...", ephemeral=True)
        else:
            msg = await ctx.respond("💽 Updating...")
        p = subprocess.Popen(["git", "pull"], stderr=subprocess.PIPE)
        _, stderr = p.communicate()
        if p.returncode != 0:
            await msg.edit(
                content=f"⚠️ Command `git pull` exited with code {p.returncode}:\n```{stderr.decode()}```"
            )
            return

        if revision:
            p = subprocess.Popen(
                ["git", "reset", "--hard", revision], stderr=subprocess.PIPE
            )
            _, stderr = p.communicate()
            if p.returncode != 0:
                await msg.edit(
                    content=f"⚠️ Command `git pull` exited with code {p.returncode}:\n```{stderr.decode()}```"
                )
                return

        p = subprocess.Popen(
            ["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            await msg.edit(
                content=f"⚠️ Command `git rev-parse HEAD` exited with code {p.returncode}:\n```{stderr.decode()}```"
            )
            return
        open(config.restartfile, "w+").close()
        await msg.edit(
            content=f"💽 Updated successfully to commit {stdout.decode()[:7]}. Restarting"
        )

    @bridge.bridge_command()
    @bridge.guild_only()
    async def prod(self, ctx: bridge.BridgeContext, *, object_to_get: str = ""):
        """Allows you to see the direct python data of certain objects"""
        if ctx.author.id not in config.SERVER_CONTROL_USERS:
            raise GameError("No permission", "You don't have permission to do that!")
        if object_to_get == "current polls":
            server = InstanceManager.current.get_or_create(ctx.guild.id)
            await ctx.reply(server.db.polls)
            return

    @tasks.loop(seconds=2, reconnect=True)
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

    @tasks.loop(seconds=15, reconnect=True)
    async def achievement_checker(self):
        for server in InstanceManager.current.instances.values():
            for user in server.db.check_achievements_list:
                defer(self.bot.award_achievements(server, user=user))
            server.db.check_achievements_list = set()

    @bridge.bridge_command()
    async def help(self, ctx: bridge.BridgeContext):
        """Shows this command"""
        help_pages = {}
        for command in self.bot.commands:
            try:
                if not await command.can_run(ctx):
                    continue
            except discord.ext.commands.CommandError:
                continue

            embed = Embed(
                title=command.name,
                description=command.help or "No description available.",
            )

            # Fucked up code I wrote a while ago
            # Works and that's about it
            command_desc = "\n!" + command.name
            type_names = {
                int: "Number",
                str: "Text",
                bool: "True or False",
                discord.member.Member: "@User",
                discord.user.User: "@User",
                discord.message.Attachment: "Message Attachment",
                discord.channel.TextChannel: "#Text Channel",
                # For BridgeOption
                "element": "Element",
                "element_name": "Element Name",
                "marked_element": "Marked Element",
            }
            first_param = True
            for name, param in command.params.items():
                if name in ["self", "ctx"]:
                    continue

                if (
                    getattr(param.annotation, "__origin__", None) is typing.Union
                    and type(None) in param.annotation.__args__
                ):  # Handle Optional type hints
                    param_type = next(
                        t for t in param.annotation.__args__ if t is not type(None)
                    )
                elif (
                    type(param.annotation).__name__ == "BridgeOption"
                ):  # I cannot figure out to import this fucking type
                    param_type = param.annotation.name
                else:
                    param_type = param.annotation
                if first_param:
                    command_desc += (
                        f" <{name.title().replace('_', ' ')} : {type_names.get(param_type, param_type)}"
                        + (" (Optional)" if param.default != inspect._empty else "")
                        + ">"
                    )
                else:
                    command_desc += (
                        f" | <{name.title().replace('_', ' ')} : {type_names.get(param_type, param_type)}"
                        + (" (Optional)" if param.default != inspect._empty else "")
                        + ">"
                    )
            embed.add_field(name="Format", value=command_desc)
            if command.aliases:
                embed.add_field(
                    name="Aliases",
                    value=format_list(["!" + i for i in command.aliases]),
                )
            if command.cog_name not in help_pages:
                help_pages[command.cog_name] = [embed]
            else:
                help_pages[command.cog_name].append(embed)

        page_groups = []
        for cog_name, command_pages in help_pages.items():
            for index, embed in enumerate(command_pages):
                embed.set_footer(
                    text=f"{index+1}/{len(command_pages)}"
                    + '\nWhen using text commands, separate each parameter with "|" '
                )
            page_groups.append(
                pages.PageGroup(
                    pages=command_pages,
                    label=cog_name,
                    loop_pages=True,
                    use_default_buttons=False,
                    custom_buttons=[
                        pages.PaginatorButton(
                            "prev",
                            emoji="<:leftarrow:1182293710684295178>",
                            style=ButtonStyle.blurple,
                        ),
                        pages.PaginatorButton(
                            "next",
                            emoji="<:rightarrow:1182293601540132945>",
                            style=ButtonStyle.blurple,
                        ),
                    ],
                )
            )

        page_groups[0].default = True

        paginator = pages.Paginator(
            pages=page_groups,
            show_menu=True,
            show_indicator=False,
            use_default_buttons=False,
            custom_buttons=[
                pages.PaginatorButton(
                    "prev",
                    emoji="<:leftarrow:1182293710684295178>",
                    style=ButtonStyle.blurple,
                ),
                pages.PaginatorButton(
                    "next",
                    emoji="<:rightarrow:1182293601540132945>",
                    style=ButtonStyle.blurple,
                ),
            ],
        )
        await paginator.respond(ctx)


def setup(client):
    client.add_cog(Main(client))
