from discord.ext import commands, tasks, bridge
from discord.utils import get
from discord import Message
from pyeod.frontend import InstanceManager, Poll
from typing import Dict

class Polls(commands.Cog):
    def __init__(self, bot):
        self.bot:bridge.AutoShardedBot = bot
        self.check_polls.start()

    @tasks.loop(seconds=1)
    async def check_polls(self):
        for guild_id, server in InstanceManager.current.instances.items():
            if not server.channels.voting_channel:
                continue
            if not server.db.polls:
                continue
            voting_channel = await self.bot.fetch_channel(server.channels.voting_channel)
            messages = await voting_channel.history(limit=50, oldest_first=True).flatten()
            # Only select bot messages
            messages = [message for message in messages if message.author.id == self.bot.user.id]
            poll_messages: Dict[Poll, Message] = {}
            for message, poll in zip(messages, server.db.polls):
                poll.votes = 0
                try:
                    downvotes = get(message.reactions, emoji = '\u2B07\uFE0F')
                    upvote_count = get(message.reactions, emoji = '\u2B06\uFE0F').count
                    downvote_count = downvotes.count
                except:
                    # TODO: handle exceptions properly
                    # Just break out of the loop if the above code breaks
                    continue
                if get(await downvotes.users().flatten(), id = poll.author.id):
                    # Double it and give it to the next person
                    poll.votes -= server.vote_req * 2
                else:
                    # Do not include the bot's own reaction
                    poll.votes += upvote_count - 1
                    poll.votes -= downvote_count - 1
                poll_messages[poll] = message
            accepted_polls = server.check_polls()
            # Delete messages before we send to news
            for poll in accepted_polls:
                await poll_messages[poll].delete()
            if server.channels.news_channel:
                news_channel = await self.bot.fetch_channel(server.channels.news_channel)
                for poll in accepted_polls:
                    await news_channel.send(server.convert_poll_to_news_message(poll))

def setup(client):
    client.add_cog(Polls(client))