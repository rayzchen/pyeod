from pyeod.frontend import DiscordGameInstance, ElementalBot, InstanceManager
from discord import Message, TextChannel, errors
from discord.ext import bridge, commands, tasks
from discord.utils import get
from typing import Optional
import traceback


class Polls(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot
        # self.check_polls.start()  # prevent double poll accepting

    async def resolve_poll(
        self,
        message: Message,
        server: DiscordGameInstance,
        news_channel: Optional[TextChannel] = None,
    ):
        if message.id in server.processing_polls:
            return
        server.processing_polls.add(message.id)
        try:
            async with server.db.poll_lock.reader:
                poll = server.poll_msg_lookup[message.id]
                poll.votes = 0
            send_news_message = True
            try:
                upvotes = get(message.reactions, emoji="\U0001F53C")
                downvotes = get(message.reactions, emoji="\U0001F53D")
                upvoters = set(u.id for u in await upvotes.users().flatten())
                downvoters = set(u.id for u in await downvotes.users().flatten())
            except Exception as e:
                # TODO: handle exceptions properly
                # Just break out of the loop if the above code breaks
                print("Ignored exception in resolve_poll")
                traceback.print_exception(type(e), e, e.__traceback__)
                return
            if get(await downvotes.users().flatten(), id=poll.author.id):
                # Double it and give it to the next person
                poll.votes = -server.vote_req * 2
                send_news_message = False
            else:
                poll.votes = upvotes.count - downvotes.count
            if await server.check_single_poll(poll):
                # Delete messages before we send to news
                await message.delete()
                async with server.db.poll_lock.writer:
                    server.poll_msg_lookup.pop(message.id)
                if send_news_message and news_channel is not None:
                    await news_channel.send(await poll.get_news_message(server))

                voters = upvoters ^ downvoters
                async with server.db.user_lock.writer:
                    for voter in voters:
                        user = await server.login_user(voter)
                        user.votes_cast_count += 1
        finally:
            server.processing_polls.remove(message.id)

    @tasks.loop(seconds=1, reconnect=True)
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
    @bridge.guild_only()
    @bridge.has_permissions(manage_messages=True)
    async def clear_polls(self, ctx: bridge.Context):
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        if server.channels.voting_channel is not None:
            channel = await self.bot.fetch_channel(server.channels.voting_channel)
            for msg_id in server.poll_msg_lookup:
                try:
                    message = await channel.fetch_message(msg_id)
                    await message.delete()
                except errors.NotFound:
                    pass
        async with server.db.poll_lock.writer:
            server.db.polls.clear()
        async with server.db.user_lock.writer:
            for user in server.db.users.values():
                user.active_polls = 0
        # TODO: delete polls and notify in news
        await ctx.respond("🧹 Cleared polls!")


def setup(client):
    client.add_cog(Polls(client))
