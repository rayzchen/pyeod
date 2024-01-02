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

    # @tasks.loop(seconds=1, reconnect=True)
    # async def check_polls(self):
    #     for server in InstanceManager.current.instances.values():
    #         if server.channels.voting_channel is None:
    #             continue
    #         if not server.db.polls:
    #             continue

    #         voting_channel = await self.bot.fetch_channel(
    #             server.channels.voting_channel
    #         )
    #         if server.channels.news_channel is not None:
    #             news_channel = await self.bot.fetch_channel(
    #                 server.channels.news_channel
    #             )
    #         else:
    #             news_channel = None
    #         messages = await voting_channel.history(
    #             limit=50, oldest_first=True
    #         ).flatten()
    #         # Only select bot messages
    #         messages = [
    #             message for message in messages if message.author.id == self.bot.user.id
    #         ]
    #         for message in messages:
    #             await self.resolve_poll(message, server, news_channel)

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
        if str(payload.emoji) not in ["\U0001F53C", "\U0001F53D"]:
            return
        if payload.message_id in server.processing_polls:
            return
        server.processing_polls.add(payload.message_id)
        print(payload.message_id)

        delete_poll = False
        silent_delete = False  # author downvoted
        async with server.db.poll_lock.reader:
            poll = server.poll_msg_lookup[payload.message_id]
            if payload.user_id == poll.author.id and str(payload.emoji) == "\U0001F53D":
                delete_poll = True
                silent_delete = True
        try:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if not silent_delete:
                print("fetch reactions")
                upvotes = get(message.reactions, emoji="\U0001F53C")
                downvotes = get(message.reactions, emoji="\U0001F53D")

                poll.votes = upvotes.count - downvotes.count
                if await server.check_single_poll(poll):
                    if server.channels.news_channel is not None:
                        print("send news")
                        news_channel = await self.bot.fetch_channel(server.channels.news_channel)
                        await news_channel.send(await poll.get_news_message(server))

                    print("fetch voters")
                    upvoters = set(u.id for u in await upvotes.users().flatten())
                    downvoters = set(u.id for u in await downvotes.users().flatten())

                    voters = upvoters ^ downvoters
                    async with server.db.user_lock.writer:
                        for voter in voters:
                            user = await server.login_user(voter)
                            user.votes_cast_count += 1

                    delete_poll = True
            if delete_poll:
                print("delete poll")
                await message.delete()
                async with server.db.poll_lock.writer:
                    server.poll_msg_lookup.pop(payload.message_id)
        except Exception as e:
            if isinstance(e, errors.NotFound):
                return
            # TODO: handle exceptions properly
            # Just break out of the loop if the above code breaks
            print("Ignored exception in resolve_poll")
            traceback.print_exception(type(e), e, e.__traceback__)
            return
        finally:
            server.processing_polls.remove(payload.message_id)

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
