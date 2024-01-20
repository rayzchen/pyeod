from pyeod import config
from pyeod.utils import format_list
from pyeod.frontend import (
    DiscordGameInstance,
    ElementalBot,
    InstanceManager,
    prepare_file,
    generate_embed_list,
    FooterPaginator,
)
from pyeod.errors import GameError
from pyeod.packer import load_instance, save_instance
from discord import (
    Attachment,
    Embed,
    File,
    Message,
    TextChannel,
    default_permissions,
    Member,
    CheckFailure,
    ButtonStyle,
)
import discord
from discord.ext import bridge, commands, tasks, pages
from typing import Optional
import io
import os
import glob
import time
import asyncio
import inspect
import typing


class Config(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot
        print("Loading instance manager")
        # Manager instance is stored under InstanceManager.current
        manager = InstanceManager()
        print("Loading instance databases")
        loop = asyncio.get_event_loop()
        loop.create_task(self.load_all_instances())
        self.load_event = asyncio.Event()

    async def load_all_instances(self):
        tic = time.perf_counter()
        with InstanceManager.current.prevent_creation():
            for file in glob.glob(os.path.join(config.package, "db", "*.eod")):
                print(os.path.basename(file))
                instance = load_instance(file)
                guild_id = int(os.path.basename(file)[:-4])
                InstanceManager.current.add_instance(guild_id, instance)
        print(f"Loaded instance databases in {time.perf_counter() - tic} seconds")
        self.load_event.set()

    @commands.Cog.listener()
    async def on_ready(self):
        if self.load_event.is_set():
            print("Awaiting load thread")
            await self.load_event.wait()
            self.load_event.clear()
            self.save.start()
            print("Started save loop")

    @tasks.loop(seconds=30, reconnect=True)
    async def save(self):
        for id, instance in InstanceManager.current.instances.items():
            await instance.db.acquire_all_locks()
            try:
                save_instance(instance, str(id) + ".eod")
            finally:
                instance.db.release_all_locks()

    # @commands.Cog.listener("on_message")
    # async def check_for_new_servers(self, msg: Message):
    #     if InstanceManager.current:  # Messages can be caught before bot is ready
    #         return
    #     await InstanceManager.current.get_or_create(msg.guild.id)

    @bridge.bridge_command(guild_ids=[config.MAIN_SERVER])
    @bridge.has_permissions(manage_guild=True)
    @bridge.guild_only()
    async def import_instance(
        self, ctx: bridge.Context, guild_id: int, file: Attachment
    ):
        """Imports an instance into a server"""
        if ctx.author.id not in config.SERVER_CONTROL_USERS:
            await ctx.respond("🔴 You don't have permission to do that!")
            return

        path = os.path.join(config.package, "db", str(guild_id) + ".eod")
        if guild_id not in InstanceManager.current.instances:
            msg = await ctx.respond("🤖 Server not found, uploading fresh database")
            old_data = None
            with open(path, "wb+") as f:
                f.write(await file.read())
        else:
            msg = await ctx.respond("🤖 Server found, backing up original database")
            with open(path, "rb") as f:
                old_data = f.read()
            with open(path, "wb") as f:
                f.write(await file.read())

        with InstanceManager.current.prevent_creation():
            instance = load_instance(path)
            if guild_id in InstanceManager.current.instances:
                InstanceManager.current.remove_instance(guild_id)
            InstanceManager.current.add_instance(guild_id, instance)

        await ctx.respond("🤖 Loaded new instance")

        if old_data is not None:
            stream = io.BytesIO(old_data)
            file = File(stream, filename=str(guild_id) + ".eod")
            await ctx.respond("🤖 Old instance backup:", file=file)


    @bridge.bridge_command()
    @bridge.guild_only()
    @bridge.has_permissions(manage_channels=True)
    async def import_inventory(
        self, ctx: bridge.Context, user: Member, inv: Attachment
    ):
        """Imports an inventory for a user"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        logged_in = await server.login_user(user.id)

        found = 0
        skipped = 0
        notfound = 0
        content = await inv.read()
        for line in content.decode("utf-8").strip().split("\n"):
            if not line:
                continue
            name = line.strip()
            if name.lower() not in server.db.elements:
                notfound += 1
            else:
                found += 1
                try:
                    await server.db.give_element(
                        logged_in, server.db.elements[name.lower()]
                    )
                except GameError as e:
                    if e.type == "Already have element":
                        found -= 1
                        skipped += 1
                    else:
                        raise

        msg = f"🤖 Successfully imported inv for user **{user.display_name}**"
        msg += f"\n> Added {found} elements"
        msg += f"\n> Skipped {skipped} elements"
        msg += f"\n> Could not find {notfound} elements"
        await ctx.respond(msg)

    @bridge.bridge_command(guild_ids=[config.MAIN_SERVER])
    @bridge.has_permissions(manage_guild=True)
    @bridge.guild_only()
    async def missing_ids(self, ctx: bridge.Context):
        server = InstanceManager.current.get_or_create(ctx.guild.id)

        async with server.db.element_lock.reader:
            all_ids = set(server.db.elem_id_lookup)
        correct_ids = set(range(1, max(all_ids) + 1))
        missing_ids = correct_ids - all_ids
        lines = [
            f"Number of elements: {len(all_ids)}",
            f"Max ID: {max(all_ids)}",
            f"Number of missing IDs: {len(missing_ids)}",
            f"Missing IDs: {sorted(missing_ids)}"
        ]
        await ctx.respond("\n".join(lines))

    @bridge.bridge_command(guild_ids=[config.MAIN_SERVER])
    @bridge.has_permissions(manage_guild=True)
    @bridge.guild_only()
    async def active_servers(self, ctx: bridge.Context):
        """Servers with the bot added"""
        if ctx.author.id not in config.SERVER_CONTROL_USERS:
            await ctx.respond("🔴 You don't have permission to do that!")
            return

        servers = InstanceManager.current.instances

        lines = []
        for guild_id, game_instance in servers.items():
            guild = await self.bot.fetch_guild(guild_id)
            lines.append(
                " ".join(
                    [
                        f"(*{guild.id}*)",
                        f"**{guild.name}** -",
                        f"__{len(game_instance.db.users)}__ users,",
                        f"__{len(game_instance.db.elements)}__ elements",
                    ]
                )
            )

        embeds = generate_embed_list(lines, f"Connected servers ({len(servers)})", 10)
        paginator = FooterPaginator(embeds, loop=False)
        await paginator.respond(ctx)

    @bridge.bridge_command(guild_ids=[config.MAIN_SERVER])
    @bridge.has_permissions(manage_guild=True)
    @bridge.guild_only()
    async def download_instance(
        self, ctx: bridge.Context, guild_id: Optional[int] = None
    ):
        """Downloads an instance"""
        if ctx.author.id not in config.SERVER_CONTROL_USERS:
            await ctx.respond("🔴 You don't have permission to do that!")
            return

        if guild_id is None:
            guild_id = ctx.guild.id

        if guild_id not in InstanceManager.current.instances:
            await ctx.respond("🔴 Server not found!")
            return

        await ctx.defer()
        path = os.path.join(config.package, "db", str(guild_id) + ".eod")
        with open(path, "rb") as f:
            data = f.read()
        stream = io.BytesIO(data)
        file = prepare_file(stream, filename=str(guild_id) + ".eod")
        await ctx.respond(f"🤖 Instance download for {guild_id}:", file=file)

    @bridge.bridge_command()
    @bridge.guild_only()
    @default_permissions(manage_channels=True)
    async def view_channels(self, ctx: bridge.Context):
        """View all currently set play channels and the servers news and voting channels"""

        def convert_channel(channel):
            if channel is None:
                return "None"
            return "<#" + str(channel) + ">"

        server = InstanceManager.current.get_or_create(ctx.guild.id)
        lines = [
            "Voting channel: " + convert_channel(server.channels.voting_channel),
            "News channel: " + convert_channel(server.channels.news_channel),
            "\nPlay channels:",
        ]

        for channel in server.channels.play_channels:
            lines.append(convert_channel(channel))
        if not len(server.channels.play_channels):
            lines.append("None added")

        embed = Embed(
            color=config.EMBED_COLOR,
            title="Registered channels",
            description="\n".join(lines),
        )
        await ctx.respond(embed=embed)

    @bridge.bridge_command()
    @bridge.guild_only()
    @default_permissions(manage_channels=True)
    async def add_play_channel(self, ctx: bridge.Context, channel: TextChannel):
        """Adds a channel to be considered a play channel"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)

        if channel.id not in server.channels.play_channels:
            server.channels.play_channels.append(channel.id)
        await ctx.respond(f"🤖 Successfully added <#{channel.id}> as a play channel!")

    @bridge.bridge_command()
    @bridge.guild_only()
    @default_permissions(manage_channels=True)
    async def remove_play_channel(self, ctx: bridge.Context, channel: TextChannel):
        """Removes a channel from being considered a play channel"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)

        if channel.id in server.channels.play_channels:
            server.channels.play_channels.remove(channel.id)
            await ctx.respond(
                f"🤖 Successfully removed <#{channel.id}> as a play channel!"
            )
        else:
            await ctx.respond(f"🔴 That is not a play channel!")

    @bridge.bridge_command()
    @bridge.guild_only()
    @default_permissions(manage_channels=True)
    async def set_news_channel(self, ctx: bridge.Context, channel: TextChannel):
        """Sets the servers news channel"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)

        server.channels.news_channel = channel.id
        await ctx.respond(f"🤖 Successfully set <#{channel.id}> as the news channel!")

    @bridge.bridge_command()
    @bridge.guild_only()
    @default_permissions(manage_channels=True)
    async def set_voting_channel(self, ctx: bridge.Context, channel: TextChannel):
        """Sets the servers voting channel"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)

        server.channels.voting_channel = channel.id
        await ctx.respond(f"🤖 Successfully set <#{channel.id}> as the voting channel!")

    @bridge.bridge_command()
    @bridge.guild_only()
    @bridge.has_permissions(manage_channels=True)
    async def edit_element_name(self, ctx: bridge.Context, elem_id: int, *, name: str):
        """Replaces an element's name"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if elem_id not in server.db.elem_id_lookup:
            await ctx.respond(f"🔴 No element with id #{elem_id}!")
            return

        async with server.db.element_lock.writer:
            element = server.db.elem_id_lookup[elem_id]
            old_name = element.name
            element.name = name
            server.db.elements.pop(old_name.lower())
            server.db.elements[name.lower()] = element
        await ctx.respond(
            f"🤖 Renamed element #{elem_id} (**{old_name}**) to **{name}** successfully!"
        )
        if server.channels.news_channel is not None:
            channel = await self.bot.fetch_channel(server.channels.news_channel)
            await channel.send(
                f"🤖 Renamed element #{elem_id} (**{old_name}**) to **{name}**"
            )

    @bridge.bridge_command()
    @bridge.guild_only()
    @bridge.has_permissions(manage_channels=True)
    async def set_vote_req(self, ctx: bridge.Context, vote_req: int):
        server = InstanceManager.current.get_or_create(ctx.guild.id)

        server.vote_req = vote_req
        await ctx.respond(f"🤖 Successfully set the vote requirement to {vote_req}")


def setup(client):
    client.add_cog(Config(client))
