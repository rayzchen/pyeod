from discord.ext import commands, tasks, bridge, pages
from discord import User, Message, TextChannel, Role, Member, Guild, SlashCommandGroup
from discord.utils import get
from pyeod.model import InternalError
from pyeod.frontend import DiscordGameInstance, InstanceManager
from pyeod.utils import format_traceback
from pyeod.packer import save_instance, load_instance
from pyeod import config
import traceback
import glob
import os


class Config(commands.Cog):
    def __init__(self, bot):
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
    
    config = SlashCommandGroup("configuration", "Bot settings for your server")
    
    @tasks.loop(seconds=5)
    async def save(self):
        for id, instance in InstanceManager.current.instances.items():
            save_instance(instance, str(id) + ".eod")

    @commands.Cog.listener("on_message")
    async def check_for_new_servers(self, msg: Message):
        if InstanceManager.current:  # Messages can be caught before bot is ready
            return
        InstanceManager.current.get_or_create(msg.guild.id, DiscordGameInstance)

    # Slash commands only cus converting to channel is busted
    @config.command()
    async def add_play_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        
        guild = await self.bot.fetch_guild(ctx.guild.id)
        
        if (
            get(guild.roles, id = server.mod_role) not in ctx.author.roles
            and ctx.author.id != guild.owner_id
        ):
            return

        server.channels.play_channels.append(channel.id)
        await ctx.respond(f"Successfully added {channel.name} as a play channel!")

    @config.command()
    async def remove_play_channel(
        self, ctx: bridge.BridgeContext, channel: TextChannel
    ):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        
        guild = await self.bot.fetch_guild(ctx.guild.id)
        
        if (
            get(guild.roles, id = server.mod_role) not in ctx.author.roles
            and ctx.author.id != guild.owner_id
        ):
            return

        try:
            server.channels.play_channels.remove(channel.id)
            await ctx.respond(f"Successfully removed {channel.name} as a play channel!")
        except ValueError:
            await ctx.respond(f"That is not a play channel")

    @config.command()
    async def set_news_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        
        
        guild = await self.bot.fetch_guild(ctx.guild.id)
        
        if (
            get(guild.roles, id = server.mod_role) not in ctx.author.roles
            and ctx.author.id != guild.owner_id
        ):
            return

        server.channels.news_channel = channel.id
        await ctx.respond(f"Successfully set {channel.name} as the news channel!")

    @config.command()
    async def set_voting_channel(self, ctx: bridge.BridgeContext, channel: TextChannel):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        
        guild = await self.bot.fetch_guild(ctx.guild.id)
        
        if (
            get(guild.roles, id = server.mod_role) not in ctx.author.roles
            and ctx.author.id != guild.owner_id
        ):
            return
        
        server.channels.voting_channel = channel.id
        await ctx.respond(f"Successfully set {channel.name} as the voting channel!")

    @config.command()
    async def set_mod_role(self, ctx: bridge.BridgeContext, role: Role):
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        
        guild = await self.bot.fetch_guild(ctx.guild.id)
        
        if (
            get(guild.roles, id = server.mod_role) not in ctx.author.roles
            and ctx.author.id != guild.owner_id
        ):
            return

        server.mod_role = int(role.id)
        
        await ctx.respond(f"Successfully set {role.name} as the moderator role!")


def setup(client):
    client.add_cog(Config(client))
