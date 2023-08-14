from discord.ext import commands, tasks, bridge
from discord import Message, TextChannel, default_permissions
from pyeod.frontend import DiscordGameInstance, InstanceManager, ElementalBot
from pyeod.packer import save_instance, load_instance
from pyeod import config
import glob
import os


class Config(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot
        print("Loading instance manager")
        # Manager instance is stored under InstanceManager.current
        manager = InstanceManager()
        print("Loading instance databases")
        for file in glob.glob(os.path.join(config.package, "db", "*.eod")):
            print(file)
            instance = load_instance(file)
            guild_id = int(os.path.basename(file)[:-4])
            manager.add_instance(guild_id, instance)
        print("Loaded instance databases")
        self.save.start()
        print("Started save loop")

    @tasks.loop(seconds=5, reconnect=True)
    async def save(self):
        for id, instance in InstanceManager.current.instances.items():
            save_instance(instance, str(id) + ".eod")

    @commands.Cog.listener("on_message")
    async def check_for_new_servers(self, msg: Message):
        if InstanceManager.current:  # Messages can be caught before bot is ready
            return
        InstanceManager.current.get_or_create(msg.guild.id, DiscordGameInstance)

    # Slash commands only cus converting to channel is busted
    @commands.slash_command()
    @default_permissions(manage_channels=True)
    async def add_play_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )

        server.channels.play_channels.append(channel.id)
        await ctx.respond(f"Successfully added {channel.name} as a play channel!")

    @commands.slash_command()
    @default_permissions(manage_channels=True)
    async def remove_play_channel(
        self, ctx: bridge.BridgeContext, channel: TextChannel
    ):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )

        try:
            server.channels.play_channels.remove(channel.id)
            await ctx.respond(f"Successfully removed {channel.name} as a play channel!")
        except ValueError:
            await ctx.respond(f"That is not a play channel")

    @commands.slash_command()
    @default_permissions(manage_channels=True)
    async def set_news_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )

        server.channels.news_channel = channel.id
        await ctx.respond(f"Successfully set {channel.name} as the news channel!")

    @commands.slash_command()
    @default_permissions(manage_channels=True)
    async def set_voting_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )

        server.channels.voting_channel = channel.id
        await ctx.respond(f"Successfully set {channel.name} as the voting channel!")

    @bridge.bridge_command()
    @default_permissions(manage_channels=True)
    async def edit_element_name(
        self, ctx: bridge.BridgeContext, elem_id: int, *, name: str
    ):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        if elem_id not in server.db.elem_id_lookup:
            await ctx.respond(f"No element with id #{elem_id}!")
            return

        element = server.db.elem_id_lookup[elem_id]
        old_name = element.name
        element.name = name
        server.db.elements.pop(old_name.lower())
        server.db.elements[name.lower()] = element
        await ctx.respond(
            f"Renamed element #{elem_id} ({old_name}) to {name} successfully!"
        )

    @bridge.bridge_command()
    @default_permissions(manage_channels=True)
    async def set_vote_req(self, ctx: bridge.BridgeContext, vote_req: int):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )

        server.vote_req = vote_req
        await ctx.respond(f"Successfully set the vote requirement to {vote_req}")

    @bridge.bridge_command()
    @default_permissions(manage_channels=True)
    async def set_max_polls(self, ctx: bridge.BridgeContext, max_polls: int):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )

        server.poll_limit = max_polls
        await ctx.respond(
            f"Successfully set the max polls a user can have to {max_polls}"
        )


def setup(client):
    client.add_cog(Config(client))
