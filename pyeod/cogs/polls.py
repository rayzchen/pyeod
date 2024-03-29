from pyeod.errors import InternalError
from pyeod.frontend import DiscordGameInstance, ElementalBot, InstanceManager
from discord import Message, TextChannel, errors
from discord.ext import bridge, commands, tasks
from discord.utils import get
from typing import Optional
import traceback


class Polls(commands.Cog):
    UPVOTE = "\U0001F53C"
    DOWNVOTE = "\U0001F53D"

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
    async def on_raw_reaction_remove(self, payload):
        if payload.guild_id not in InstanceManager.current.instances:
            return
        server = InstanceManager.current.instances[payload.guild_id]
        if server.channels.voting_channel != payload.channel_id:
            return
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) not in [Polls.UPVOTE, Polls.DOWNVOTE]:
            return
        if payload.message_id not in server.poll_msg_lookup:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if message.author.id == self.bot.user.id:
                await message.delete()
            return

        if str(payload.emoji) == Polls.UPVOTE:
            if payload.user_id in server.upvoters[payload.message_id]:
                server.upvoters[payload.message_id].remove(payload.user_id)
        else:
            if payload.user_id in server.downvoters[payload.message_id]:
                server.downvoters[payload.message_id].remove(payload.user_id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.guild_id not in InstanceManager.current.instances:
            return
        server = InstanceManager.current.instances[payload.guild_id]
        if server.channels.voting_channel != payload.channel_id:
            return
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) not in [Polls.UPVOTE, Polls.DOWNVOTE]:
            return
        if payload.message_id not in server.poll_msg_lookup:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if message.author.id == self.bot.user.id:
                await message.delete()
            return

        if str(payload.emoji) == Polls.UPVOTE:
            server.upvoters[payload.message_id].add(payload.user_id)
        else:
            server.downvoters[payload.message_id].add(payload.user_id)
        if payload.message_id in server.processing_polls:
            return
        server.processing_polls.add(payload.message_id)

        voters = (
            server.upvoters[payload.message_id] ^ server.downvoters[payload.message_id]
        )

        resolve_poll = False
        author_downvote = False
        async with server.db.poll_lock.reader:
            poll = server.poll_msg_lookup[payload.message_id]
            if (
                payload.user_id == poll.author.id
                and str(payload.emoji) == Polls.DOWNVOTE
            ):
                author_downvote = True
        poll.votes = len(server.upvoters[payload.message_id]) - len(
            server.downvoters[payload.message_id]
        )
        if not author_downvote and abs(poll.votes) < server.vote_req:
            # Quit early
            server.processing_polls.remove(payload.message_id)
            return

        try:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            await message.delete()
            async with server.db.poll_lock.writer:
                server.poll_msg_lookup.pop(payload.message_id)
                server.upvoters.pop(payload.message_id)
                server.downvoters.pop(payload.message_id)
            if author_downvote:
                async with server.db.user_lock.writer:
                    # Decrease active poll count
                    author = await server.login_user(payload.user_id)
                    author.active_polls -= 1
            else:
                # upvotes = get(message.reactions, emoji=Polls.UPVOTE)
                # downvotes = get(message.reactions, emoji=Polls.DOWNVOTE)

                # poll.votes = (upvotes.count if upvotes else 0) - (downvotes.count if downvotes else 0)
                try:
                    resolve_poll = await server.check_single_poll(poll)
                except InternalError as e:
                    if e.type == "Combo exists":
                        resolve_poll = False
                    else:
                        raise

                if resolve_poll:
                    if server.channels.news_channel is not None:
                        news_channel = await self.bot.fetch_channel(
                            server.channels.news_channel
                        )
                        news_message = await poll.get_news_message(server)
                        if not poll.accepted:
                            server.polls_rejected += 1
                        if isinstance(news_message, tuple):  # (msg, embed)
                            await news_channel.send(
                                news_message[0], embed=news_message[1]
                            )
                        else:
                            await news_channel.send(news_message)

                    async with server.db.user_lock.writer:
                        for voter in voters:
                            user = await server.login_user(voter)
                            user.votes_cast_count += 1

            # Author deleted, or poll resolved
            if resolve_poll:
                for user_id in list(voters) + [poll.author.id]:
                    user = await server.login_user(user_id)
                    #await self.bot.award_achievements(server, user=user)
        except Exception as e:
            if isinstance(e, errors.NotFound):
                return
            print("Ignored exception in resolve_poll")
            traceback.print_exception(type(e), e, e.__traceback__)
            return
        finally:
            server.processing_polls.remove(payload.message_id)

    @bridge.bridge_command()
    @bridge.guild_only()
    @bridge.has_permissions(manage_messages=True)
    async def clear_polls(self, ctx: bridge.Context):
        """Clears all current polls in the poll channel"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        # Prevent new polls
        async with server.db.poll_lock.writer:
            if server.channels.voting_channel is not None:
                channel = await self.bot.fetch_channel(server.channels.voting_channel)
                for msg_id in server.poll_msg_lookup:
                    try:
                        message = await channel.fetch_message(msg_id)
                        await message.delete()
                    except errors.NotFound:
                        pass
                server.poll_msg_lookup.clear()
                server.upvoters.clear()
                server.downvoters.clear()
            server.db.polls.clear()
        async with server.db.user_lock.writer:
            for user in server.db.users.values():
                user.active_polls = 0
        # TODO: delete polls and notify in news
        await ctx.respond("🧹 Cleared polls!")


def setup(client):
    client.add_cog(Polls(client))
