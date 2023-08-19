from discord.ext import commands, tasks, bridge
from discord.utils import get
from discord import Message, TextChannel, errors, default_permissions
from pyeod.frontend import InstanceManager, DiscordGameInstance, ElementalBot
from typing import Optional


class Polls(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot
        # self.check_polls.start()

    @tasks.loop(seconds=1)
    async def check_polls(self):
        for server in InstanceManager.current.instances.values():
            if server.channels.voting_channel is None:
                continue
            if not server.db.polls:
                continue

            voting_channel = await self.bot.fetch_channel(
                server.channels.voting_channel
            )
            if server.channels.news_channel is not None:
                news_channel = await self.bot.fetch_channel(
                    server.channels.news_channel
                )
            else:
                news_channel = None
            messages = await voting_channel.history(
                limit=50, oldest_first=True
            ).flatten()
            # Only select bot messages
            messages = [
                message for message in messages if message.author.id == self.bot.user.id
            ]
            for message in messages:
                await self.resolve_poll(message, server, news_channel)

    async def resolve_poll(
        self,
        message: Message,
        server: DiscordGameInstance,
        news_channel: Optional[TextChannel] = None,
    ):
        poll = server.poll_msg_lookup[message.id]
        poll.votes = 0
        send_news_message = True
        try:
            downvotes = get(message.reactions, emoji="\U0001F53D")
            upvote_count = get(message.reactions, emoji="\U0001F53C").count
            downvote_count = downvotes.count
        except:
            # TODO: handle exceptions properly
            # Just break out of the loop if the above code breaks
            return
        if get(await downvotes.users().flatten(), id=poll.author.id):
            # Double it and give it to the next person
            poll.votes -= server.vote_req * 2
            send_news_message = False
        else:
            # Do not include the bot's own reaction
            poll.votes += upvote_count - 1
            poll.votes -= downvote_count - 1
        if server.check_single_poll(poll):
            # Delete messages before we send to news
            await message.delete()
            server.poll_msg_lookup.pop(message.id)
            if send_news_message and news_channel is not None:
                await news_channel.send(poll.get_news_message(server))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.guild_id not in InstanceManager.current.instances:
            return
        server = InstanceManager.current.instances[payload.guild_id]
        if server.channels.voting_channel != payload.channel_id:
            return
        if payload.user_id == self.bot.user.id:
            return
        if payload.message_id not in server.poll_msg_lookup:
            return

        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        if server.channels.news_channel is not None:
            news_channel = await self.bot.fetch_channel(server.channels.news_channel)
        else:
            news_channel = None
        await self.resolve_poll(message, server, news_channel)

    @bridge.bridge_command()
    @default_permissions(manage_messages=True)
    async def clear_polls(self, ctx: bridge.BridgeContext):
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if server.channels.voting_channel is not None:
            channel = await self.bot.fetch_channel(server.channels.voting_channel)
            for msg_id in server.poll_msg_lookup:
                try:
                    message = await channel.fetch_message(msg_id)
                    await message.delete()
                except errors.NotFound:
                    pass
        server.db.polls.clear()
        for user in server.db.users.values():
            user.active_polls = 0
        # TODO: delete polls and notify in news
        await ctx.reply("🧹 Cleared polls!")


def setup(client):
    client.add_cog(Polls(client))
