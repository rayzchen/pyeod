from discord.ext import commands, tasks, bridge
from discord.utils import get
from discord import Message, TextChannel, default_permissions
from pyeod.frontend import DiscordGameInstance, InstanceManager
from pyeod.packer import save_instance, load_instance
from pyeod import config
import glob
import os

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
            messages = [message for message in messages if message.author.id == self.bot.user.id]#Filter out non bot messages
            poll_dict = {}
            for message, poll in zip(messages, server.db.polls):
                poll.votes = 0
                try:
                    upvote_count = get(message.reactions, emoji = '\u2B06\uFE0F').count
                    downvote_count = get(message.reactions, emoji = '\u2B07\uFE0F').count
                except:
                    continue#Just break out of the loop if the above code breaks
                if upvote_count != None and downvote_count != None:
                    poll.votes += upvote_count - 1# Do not include the bot's own reaction
                    poll.votes -= downvote_count - 1
                poll_dict[poll] = message
            news_polls = []
            for i in server.check_polls():#Delete messages before we send to news
                await poll_dict[i].delete()
                news_polls.append(i)
            if server.channels.news_channel:
                news_channel = await self.bot.fetch_channel(server.channels.news_channel)
                for i in news_polls:
                    await news_channel.send(server.convert_poll_to_news_message(i))
                
def setup(client):
    client.add_cog(Polls(client))